"""
simulation_engine/simulator.py

The EV Simulation Engine — takes raw telemetry and scenario params,
runs physics-based computations, and returns a complete simulation result.

This is the orchestrator that ties together:
- telemetry_generator  → raw time-series data
- physics computations → derived quantities per step
- aggregated results   → summary stats for the metrics engine

Output schema
-------------
{
    "telemetry":        List[dict],   # enriched time-series
    "summary": {
        "total_distance_km":     float,
        "total_energy_kwh":      float,
        "avg_speed_kmh":         float,
        "avg_temp_c":            float,
        "max_temp_c":            float,
        "min_battery_pct":       float,
        "total_regen_kwh":       float,
        "total_charge_kwh":      float,
        "charging_events":       int,
        "thermal_violations":    int,   # steps above safe threshold
        "critical_violations":   int,   # steps above critical threshold
        "avg_voltage_v":         float,
        "voltage_std_v":         float,
        "thermal_std_c":         float,
        "energy_per_km":         float,
        "regen_recovery_pct":    float, # regen as % of total energy used
    },
    "params":           dict,         # original scenario params
    "scenario_label":   str,          # human-readable scenario name
}
"""

import time
import numpy as np
from typing import List

from config import (
    SIM_TIME_STEP_MINUTES,
    BATTERY_CAPACITY_KWH,
    BATTERY_NOMINAL_VOLTAGE,
    THERMAL_SAFE_MAX_C,
    THERMAL_CRITICAL_C,
)
from simulation_engine.telemetry_generator import generate_telemetry


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def run_simulation(params: dict, seed: int = 42) -> dict:
    """
    Run a full EV simulation from scenario parameters.

    Parameters
    ----------
    params : dict
        Validated scenario parameters from scenario_parser.parse_scenario()
    seed : int
        Random seed passed to telemetry generator

    Returns
    -------
    dict — complete simulation result (telemetry + summary + metadata)
    """
    t_start = time.time()

    # Step 1 — generate raw telemetry
    telemetry = generate_telemetry(params, seed=seed)

    # Step 2 — enrich each step with derived quantities
    telemetry = _enrich_telemetry(telemetry, params)

    # Step 3 — compute summary statistics
    summary = _compute_summary(telemetry, params)

    # Step 4 — build scenario label for display
    label = _build_scenario_label(params)

    duration_sec = round(time.time() - t_start, 3)

    return {
        "telemetry":      telemetry,
        "summary":        summary,
        "params":         params,
        "scenario_label": label,
        "duration_sec":   duration_sec,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Telemetry enrichment
# ─────────────────────────────────────────────────────────────────────────────

def _enrich_telemetry(telemetry: List[dict], params: dict) -> List[dict]:
    """
    Add derived fields to each telemetry row:
    - distance_km        cumulative distance travelled
    - energy_kwh         cumulative energy consumed
    - power_kw           instantaneous power draw
    - thermal_status     "normal" | "warning" | "critical"
    - battery_status     "healthy" | "low" | "critical"
    - regen_cumulative   cumulative regen energy recovered
    """
    dt_hours         = SIM_TIME_STEP_MINUTES / 60.0
    cumulative_dist  = 0.0
    cumulative_energy = 0.0
    cumulative_regen  = 0.0

    for i, row in enumerate(telemetry):

        # ── Distance ─────────────────────────────────────────────────────────
        step_dist_km      = row["speed_kmh"] * dt_hours
        cumulative_dist  += step_dist_km
        row["distance_km"] = round(cumulative_dist, 3)

        # ── Power & Energy ────────────────────────────────────────────────────
        if row["is_charging"]:
            power_kw = -row["charge_rate_kw"]   # negative = energy flowing in
        else:
            # P = V × I  (kW)
            power_kw = (row["voltage_v"] * row["current_a"]) / 1000.0

        row["power_kw"] = round(power_kw, 3)

        # Only count discharge toward energy consumed
        if power_kw > 0:
            cumulative_energy += power_kw * dt_hours
        row["energy_kwh"] = round(cumulative_energy, 4)

        # ── Regen ─────────────────────────────────────────────────────────────
        cumulative_regen       += row["regen_kw"] * dt_hours
        row["regen_cumulative"] = round(cumulative_regen, 4)

        # ── Thermal status ────────────────────────────────────────────────────
        if row["temp_c"] >= THERMAL_CRITICAL_C:
            row["thermal_status"] = "critical"
        elif row["temp_c"] >= THERMAL_SAFE_MAX_C:
            row["thermal_status"] = "warning"
        else:
            row["thermal_status"] = "normal"

        # ── Battery status ────────────────────────────────────────────────────
        if row["battery_pct"] <= 10:
            row["battery_status"] = "critical"
        elif row["battery_pct"] <= 25:
            row["battery_status"] = "low"
        else:
            row["battery_status"] = "healthy"

        # ── State of health proxy (degradation per step) ──────────────────────
        # Combines thermal stress + high C-rate charging as a degradation signal
        thermal_stress = max(0, row["temp_c"] - THERMAL_SAFE_MAX_C) * 0.002
        charge_stress  = (row["charge_rate_kw"] / 150.0) * 0.001 if row["is_charging"] else 0
        row["degradation_signal"] = round(thermal_stress + charge_stress, 5)

    return telemetry


# ─────────────────────────────────────────────────────────────────────────────
# Summary statistics
# ─────────────────────────────────────────────────────────────────────────────

def _compute_summary(telemetry: List[dict], params: dict) -> dict:
    """Aggregate the enriched telemetry into scalar summary statistics."""

    speeds         = np.array([r["speed_kmh"]      for r in telemetry])
    temps          = np.array([r["temp_c"]          for r in telemetry])
    batteries      = np.array([r["battery_pct"]     for r in telemetry])
    voltages       = np.array([r["voltage_v"]       for r in telemetry])
    powers         = np.array([r["power_kw"]        for r in telemetry])
    regens         = np.array([r["regen_kw"]        for r in telemetry])
    charge_rates   = np.array([r["charge_rate_kw"]  for r in telemetry])
    degradations   = np.array([r["degradation_signal"] for r in telemetry])

    dt_hours       = SIM_TIME_STEP_MINUTES / 60.0

    total_distance = float(telemetry[-1]["distance_km"])
    total_energy   = float(telemetry[-1]["energy_kwh"])
    total_regen    = float(telemetry[-1]["regen_cumulative"])
    total_charge   = float(np.sum(charge_rates) * dt_hours)

    charging_steps = sum(1 for r in telemetry if r["is_charging"])
    # Count charging events (transitions into charging state)
    charging_events = sum(
        1 for i in range(1, len(telemetry))
        if telemetry[i]["is_charging"] and not telemetry[i - 1]["is_charging"]
    )

    thermal_violations  = int(np.sum(temps >= THERMAL_SAFE_MAX_C))
    critical_violations = int(np.sum(temps >= THERMAL_CRITICAL_C))

    energy_per_km = (total_energy / total_distance) if total_distance > 0 else 0.0
    regen_recovery_pct = (total_regen / total_energy * 100) if total_energy > 0 else 0.0

    # Voltage and thermal consistency (lower std = more stable)
    voltage_std = float(np.std(voltages))
    thermal_std = float(np.std(temps))

    # Cumulative degradation signal
    total_degradation = float(np.sum(degradations))

    # Battery swing — how much SoC changed overall
    battery_swing = float(batteries[0] - batteries[-1])

    return {
        "total_distance_km":   round(total_distance, 2),
        "total_energy_kwh":    round(total_energy, 3),
        "avg_speed_kmh":       round(float(np.mean(speeds)), 2),
        "max_speed_kmh":       round(float(np.max(speeds)), 2),
        "avg_temp_c":          round(float(np.mean(temps)), 2),
        "max_temp_c":          round(float(np.max(temps)), 2),
        "min_temp_c":          round(float(np.min(temps)), 2),
        "min_battery_pct":     round(float(np.min(batteries)), 2),
        "final_battery_pct":   round(float(batteries[-1]), 2),
        "battery_swing_pct":   round(battery_swing, 2),
        "total_regen_kwh":     round(total_regen, 3),
        "total_charge_kwh":    round(total_charge, 3),
        "charging_events":     charging_events,
        "charging_steps":      charging_steps,
        "thermal_violations":  thermal_violations,
        "critical_violations": critical_violations,
        "avg_voltage_v":       round(float(np.mean(voltages)), 2),
        "voltage_std_v":       round(voltage_std, 3),
        "thermal_std_c":       round(thermal_std, 3),
        "energy_per_km":       round(energy_per_km, 4),
        "regen_recovery_pct":  round(regen_recovery_pct, 2),
        "total_degradation":   round(total_degradation, 5),
        "avg_power_kw":        round(float(np.mean(powers[powers > 0])) if np.any(powers > 0) else 0.0, 2),
        "peak_power_kw":       round(float(np.max(powers)), 2),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Scenario label builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_scenario_label(params: dict) -> str:
    """
    Build a compact human-readable label for a scenario.
    Example: "Aggressive | Hilly | Heavy traffic | 42°C | Fast charging"
    """
    parts = [
        params["driving_style"].capitalize(),
        params["terrain"].capitalize(),
        params["traffic"].replace("_", "-").capitalize() + " traffic",
        f"{params['temperature_c']}°C",
    ]
    if params["charging_mode"] != "none":
        parts.append(params["charging_mode"].replace("_", " ").capitalize() + " charging")
    if params["weather"] != "clear":
        parts.append(params["weather"].capitalize())

    return " | ".join(parts)