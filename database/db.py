"""
database/db.py — SQLite persistence for GenEV simulation runs.

Tables
------
simulation_runs  — one row per run (prompt, params, metrics, insights)
telemetry_points — time-series data per run (FK to simulation_runs)
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional

from config import DB_PATH


# ─────────────────────────────────────────────────────────────────────────────
# Schema
# ─────────────────────────────────────────────────────────────────────────────

_DDL = """
CREATE TABLE IF NOT EXISTS simulation_runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at   TEXT    NOT NULL,
    prompt       TEXT    NOT NULL,
    params       TEXT    NOT NULL,
    metrics      TEXT    NOT NULL,
    insights     TEXT    NOT NULL,
    duration_sec REAL
);

CREATE TABLE IF NOT EXISTS telemetry_points (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id         INTEGER NOT NULL REFERENCES simulation_runs(id) ON DELETE CASCADE,
    time_min       REAL NOT NULL,
    speed_kmh      REAL,
    battery_pct    REAL,
    voltage_v      REAL,
    temp_c         REAL,
    current_a      REAL,
    charge_rate_kw REAL,
    regen_kw       REAL,
    is_charging    INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_telemetry_run ON telemetry_points(run_id);
"""


# ─────────────────────────────────────────────────────────────────────────────
# Connection helper
# ─────────────────────────────────────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create tables if they don't exist. Call once at app startup."""
    with _connect() as conn:
        conn.executescript(_DDL)


# ─────────────────────────────────────────────────────────────────────────────
# Write
# ─────────────────────────────────────────────────────────────────────────────

def save_run(
    prompt: str,
    params: dict,
    metrics: dict,
    insights: list[str],
    telemetry: list[dict],
    duration_sec: Optional[float] = None,
) -> int:
    """
    Persist a complete simulation run.
    Returns the new run_id.
    """
    now = datetime.utcnow().isoformat()

    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO simulation_runs
                (created_at, prompt, params, metrics, insights, duration_sec)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                now,
                prompt,
                json.dumps(params),
                json.dumps(metrics),
                json.dumps(insights),
                duration_sec,
            ),
        )
        run_id: int = cur.lastrowid

        conn.executemany(
            """
            INSERT INTO telemetry_points
                (run_id, time_min, speed_kmh, battery_pct, voltage_v,
                 temp_c, current_a, charge_rate_kw, regen_kw, is_charging)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    run_id,
                    row["time_min"],
                    row.get("speed_kmh"),
                    row.get("battery_pct"),
                    row.get("voltage_v"),
                    row.get("temp_c"),
                    row.get("current_a"),
                    row.get("charge_rate_kw"),
                    row.get("regen_kw"),
                    int(row.get("is_charging", False)),
                )
                for row in telemetry
            ],
        )

    return run_id


# ─────────────────────────────────────────────────────────────────────────────
# Read
# ─────────────────────────────────────────────────────────────────────────────

def get_all_runs(limit: int = 50) -> list[dict]:
    """Return summary rows for the history sidebar (no telemetry)."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, prompt, metrics
            FROM simulation_runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [
        {
            "id": r["id"],
            "created_at": r["created_at"],
            "prompt": r["prompt"],
            "metrics": json.loads(r["metrics"]),
        }
        for r in rows
    ]


def get_run_by_id(run_id: int) -> Optional[dict]:
    """Return a full run including telemetry, or None if not found."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM simulation_runs WHERE id = ?", (run_id,)
        ).fetchone()

        if row is None:
            return None

        telemetry_rows = conn.execute(
            """
            SELECT time_min, speed_kmh, battery_pct, voltage_v,
                   temp_c, current_a, charge_rate_kw, regen_kw, is_charging
            FROM telemetry_points
            WHERE run_id = ?
            ORDER BY time_min
            """,
            (run_id,),
        ).fetchall()

    return {
        "id":          row["id"],
        "created_at":  row["created_at"],
        "prompt":      row["prompt"],
        "params":      json.loads(row["params"]),
        "metrics":     json.loads(row["metrics"]),
        "insights":    json.loads(row["insights"]),
        "duration_sec":row["duration_sec"],
        "telemetry": [
            {**dict(t), "is_charging": bool(t["is_charging"])}
            for t in telemetry_rows
        ],
    }


def get_runs_for_comparison(run_ids: list[int]) -> list[dict]:
    """Return full runs for a list of IDs — used by the comparison panel."""
    return [r for rid in run_ids if (r := get_run_by_id(rid)) is not None]


def delete_run(run_id: int) -> None:
    """Delete a run and its telemetry (cascade handles child rows)."""
    with _connect() as conn:
        conn.execute("DELETE FROM simulation_runs WHERE id = ?", (run_id,))