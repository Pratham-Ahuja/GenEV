"""
frontend/components/comparison.py

Scenario comparison UI component for GenEV.

Features
--------
1. Run selector       — pick up to 4 past runs from history
2. Metric diff table  — side-by-side metric comparison with delta indicators
3. Comparison charts  — grouped bar chart + overlaid telemetry lines
4. Winner summary     — which scenario performed best per metric
"""

import streamlit as st
import plotly.graph_objects as go
from typing import List

from database.db import get_runs_for_comparison, get_all_runs
from frontend.components.charts import comparison_bar_chart, _COLORS, _base_layout


# ─────────────────────────────────────────────────────────────────────────────
# Colour helpers
# ─────────────────────────────────────────────────────────────────────────────

_RUN_COLORS = [
    _COLORS["green"],
    _COLORS["blue"],
    _COLORS["purple"],
    _COLORS["orange"],
]

def _delta_html(val: float, ref: float, higher_better: bool = True) -> str:
    """
    Render a delta pill comparing val to ref.
    Green = better, red = worse, grey = same.
    """
    delta = val - ref
    if abs(delta) < 0.5:
        return '<span style="color:#64748B; font-size:11px;">  —</span>'

    better = (delta > 0) if higher_better else (delta < 0)
    color  = "#1D9E75" if better else "#DC2626"
    sign   = "+" if delta > 0 else ""
    return f'<span style="color:{color}; font-size:11px; font-weight:500;"> {sign}{delta:.1f}</span>'


def _score_color(value: float, higher_better: bool = True) -> str:
    v = value if higher_better else (100 - value)
    if v >= 75: return "#1D9E75"
    if v >= 50: return "#D97706"
    return "#DC2626"


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def render_comparison_panel() -> None:
    """
    Full comparison panel — call this from app.py inside the
    Comparison tab. Handles its own data fetching and state.
    """
    st.markdown("### 🔀 Scenario Comparison")
    st.markdown(
        "Select up to **4 past runs** to compare side-by-side. "
        "Deltas are shown relative to the first selected run.",
        unsafe_allow_html=False,
    )

    # ── Fetch history ─────────────────────────────────────────────────────────
    all_runs = get_all_runs(limit=50)

    if len(all_runs) < 2:
        st.info(
            "Run at least **2 simulations** to enable comparison. "
            "Head back to the Simulator tab and try different scenarios.",
            icon="ℹ️",
        )
        return

    # ── Run selector ──────────────────────────────────────────────────────────
    run_options = {
        f"#{r['id']} — {r['prompt'][:60]}{'...' if len(r['prompt']) > 60 else ''}": r["id"]
        for r in all_runs
    }

    selected_labels = st.multiselect(
        label="Select runs to compare",
        options=list(run_options.keys()),
        default=list(run_options.keys())[:2],
        max_selections=4,
        help="Pick 2–4 runs. Deltas are relative to the first selection.",
    )

    if len(selected_labels) < 2:
        st.warning("Please select at least 2 runs to compare.", icon="⚠️")
        return

    selected_ids = [run_options[lbl] for lbl in selected_labels]

    # ── Fetch full run data ───────────────────────────────────────────────────
    runs = get_runs_for_comparison(selected_ids)

    if len(runs) < 2:
        st.error("Could not load run data. Please try again.", icon="🔴")
        return

    # ── Render sections ───────────────────────────────────────────────────────
    _render_scenario_labels(runs)
    st.divider()
    _render_metric_diff_table(runs)
    st.divider()
    _render_comparison_charts(runs)
    st.divider()
    _render_telemetry_overlay(runs)
    st.divider()
    _render_winner_summary(runs)


# ─────────────────────────────────────────────────────────────────────────────
# Section 1 — Scenario label cards
# ─────────────────────────────────────────────────────────────────────────────

def _render_scenario_labels(runs: List[dict]) -> None:
    """Render a coloured label card for each selected run."""
    cols = st.columns(len(runs))
    for i, (col, run) in enumerate(zip(cols, runs)):
        color   = _RUN_COLORS[i % len(_RUN_COLORS)]
        label   = run.get("params", {})
        created = run.get("created_at", "")[:16].replace("T", " ")

        with col:
            st.markdown(f"""
            <div style="
                border-left: 4px solid {color};
                background: rgba(255,255,255,0.03);
                border-radius: 8px;
                padding: 12px 14px;
                margin-bottom: 8px;
            ">
                <div style="font-size:11px; color:{color};
                            font-weight:600; margin-bottom:4px;">
                    RUN #{run['id']}
                </div>
                <div style="font-size:12px; color:#CBD5E1; line-height:1.5;">
                    {run.get('params', {}).get('driving_style','').capitalize()}
                    · {run.get('params', {}).get('terrain','').capitalize()}
                    · {run.get('params', {}).get('temperature_c','')}°C
                </div>
                <div style="font-size:10px; color:#64748B; margin-top:4px;">
                    {created} UTC
                </div>
            </div>
            """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Section 2 — Metric diff table
# ─────────────────────────────────────────────────────────────────────────────

def _render_metric_diff_table(runs: List[dict]) -> None:
    """
    Side-by-side metric table.
    First run is the reference; subsequent runs show Δ relative to it.
    """
    st.markdown("#### 📊 Metric Comparison")

    metric_defs = [
        ("overall_score",        "Overall Score",        True,  "/100"),
        ("efficiency_score",     "Efficiency Score",     True,  "/100"),
        ("battery_stress_index", "Battery Stress Index", False, "/100"),
        ("thermal_risk_pct",     "Thermal Risk",         False, "%"),
        ("stability_score",      "Stability Score",      True,  "/100"),
        ("charging_efficiency",  "Charging Efficiency",  True,  "%"),
        ("ai_optimization_gain", "AI Gain",              True,  "%"),
    ]

    # Header row
    run_headers = "".join([
        f'<th style="text-align:center;color:{_RUN_COLORS[i]};'
        f'font-size:12px;padding:8px 12px;">Run #{r["id"]}</th>'
        for i, r in enumerate(runs)
    ])

    header = (
        f'<tr style="border-bottom:1px solid #E2E8F0;">'
        f'<th style="text-align:left;color:#0A0A0A;font-size:12px;padding:8px 12px;">Metric</th>'
        f'{run_headers}'
        f'</tr>'
    )

    ref_metrics = runs[0].get("metrics", {})
    rows_html   = ""

    for i, (key, label, higher_better, unit) in enumerate(metric_defs):
        bg = "#F8FAFC" if i % 2 == 0 else "#FFFFFF"

        cells = (
            f'<td style="padding:9px 12px;font-size:13px;color:#0A0A0A;'
            f'border-bottom:1px solid #E2E8F0;">{label}</td>'
        )

        for j, run in enumerate(runs):
            m     = run.get("metrics", {})
            val   = m.get(key, 0)
            color = _score_color(val, higher_better)

            if j == 0:
                delta_html = ""
            else:
                ref_val    = ref_metrics.get(key, 0)
                delta_html = _delta_html(val, ref_val, higher_better)

            cells += (
                f'<td style="text-align:center;padding:9px 12px;'
                f'border-bottom:1px solid #E2E8F0;">'
                f'<span style="font-size:14px;font-weight:600;color:{color};">{val:.1f}</span>'
                f'<span style="font-size:11px;color:#475569;">{unit}</span>'
                f'{delta_html}'
                f'</td>'
            )

        rows_html += f'<tr style="background:{bg};">{cells}</tr>'

    st.markdown(
        f'<div style="border:1px solid #E2E8F0;border-radius:12px;'
        f'overflow-x:auto;margin-bottom:16px;">'
        f'<table style="width:100%;border-collapse:collapse;">'
        f'<thead>{header}</thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table></div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Section 3 — Comparison bar chart
# ─────────────────────────────────────────────────────────────────────────────

def _render_comparison_charts(runs: List[dict]) -> None:
    """Render the grouped bar chart from charts.py."""
    st.markdown("#### 📊 Visual Comparison")

    # Attach scenario label to each run for the chart legend
    enriched = []
    for run in runs:
        p = run.get("params", {})
        run["scenario_label"] = (
            f"#{run['id']} {p.get('driving_style','').capitalize()} "
            f"· {p.get('terrain','').capitalize()} · {p.get('temperature_c','')}°C"
        )
        enriched.append(run)

    fig = comparison_bar_chart(enriched)
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# Section 4 — Telemetry overlay
# ─────────────────────────────────────────────────────────────────────────────

def _render_telemetry_overlay(runs: List[dict]) -> None:
    """
    Overlay battery % and temperature curves from all selected runs
    on shared axes for direct visual comparison.
    """
    st.markdown("#### 📈 Telemetry Overlay")

    col1, col2 = st.columns(2)

    with col1:
        fig_bat = go.Figure()
        for i, run in enumerate(runs):
            telem = run.get("telemetry", [])
            if not telem:
                continue
            color  = _RUN_COLORS[i % len(_RUN_COLORS)]
            times  = [r["time_min"] for r in telem]
            batt   = [r["battery_pct"] for r in telem]
            p      = run.get("params", {})
            label  = f"#{run['id']} {p.get('driving_style','')}"

            fig_bat.add_trace(go.Scatter(
                x=times, y=batt,
                mode="lines",
                name=label,
                line=dict(color=color, width=2, shape="spline"),
            ))

        fig_bat.update_layout(**_base_layout(
            title=dict(text="🔋 Battery % Overlay", font=dict(size=13)),
            yaxis=dict(
                title="Battery (%)",
                range=[0, 105],
                gridcolor=_COLORS["border"],
                tickfont=dict(size=10, color=_COLORS["text_muted"]),
            ),
            xaxis=dict(
                title="Time (min)",
                gridcolor=_COLORS["border"],
                tickfont=dict(size=10, color=_COLORS["text_muted"]),
            ),
            legend=dict(
                font=dict(size=10),
                bgcolor="rgba(0,0,0,0)",
            ),
        ))
        st.plotly_chart(fig_bat, use_container_width=True)

    with col2:
        fig_temp = go.Figure()

        # Safe threshold band
        fig_temp.add_hline(
            y=45, line_dash="dot", line_color="#D97706",
            annotation_text="Safe max",
            annotation_font=dict(size=9, color="#D97706"),
        )

        for i, run in enumerate(runs):
            telem = run.get("telemetry", [])
            if not telem:
                continue
            color  = _RUN_COLORS[i % len(_RUN_COLORS)]
            times  = [r["time_min"] for r in telem]
            temps  = [r["temp_c"]   for r in telem]
            p      = run.get("params", {})
            label  = f"#{run['id']} {p.get('driving_style','')}"

            fig_temp.add_trace(go.Scatter(
                x=times, y=temps,
                mode="lines",
                name=label,
                line=dict(color=color, width=2, shape="spline"),
            ))

        fig_temp.update_layout(**_base_layout(
            title=dict(text="🌡️ Temperature Overlay", font=dict(size=13)),
            yaxis=dict(
                title="Temperature (°C)",
                gridcolor=_COLORS["border"],
                tickfont=dict(size=10, color=_COLORS["text_muted"]),
            ),
            xaxis=dict(
                title="Time (min)",
                gridcolor=_COLORS["border"],
                tickfont=dict(size=10, color=_COLORS["text_muted"]),
            ),
            legend=dict(
                font=dict(size=10),
                bgcolor="rgba(0,0,0,0)",
            ),
        ))
        st.plotly_chart(fig_temp, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# Section 5 — Winner summary
# ─────────────────────────────────────────────────────────────────────────────

def _render_winner_summary(runs: List[dict]) -> None:
    """
    Show which run won each metric category.
    Displayed as a compact trophy-style table.
    """
    st.markdown("#### 🏆 Category Winners")

    metric_defs = [
        ("overall_score",        "Overall Score",       True),
        ("efficiency_score",     "Best Efficiency",     True),
        ("battery_stress_index", "Lowest Stress",       False),
        ("thermal_risk_pct",     "Safest Thermal",      False),
        ("stability_score",      "Most Stable",         True),
        ("charging_efficiency",  "Best Charging",       True),
    ]

    winners_html = ""
    for key, label, higher_better in metric_defs:
        values = [(run["id"], run.get("metrics", {}).get(key, 0)) for run in runs]
        winner_id, winner_val = (
            max(values, key=lambda x: x[1]) if higher_better
            else min(values, key=lambda x: x[1])
        )

        # Find color for this run
        winner_idx = next(
            (i for i, r in enumerate(runs) if r["id"] == winner_id), 0
        )
        color = _RUN_COLORS[winner_idx % len(_RUN_COLORS)]

        winners_html += f"""
        <div style="
            display:flex;
            justify-content:space-between;
            align-items:center;
            padding:9px 14px;
            border-bottom:1px solid rgba(255,255,255,0.04);
        ">
            <span style="font-size:13px; color:#94A3B8;">{label}</span>
            <span style="
                background:rgba(255,255,255,0.05);
                border:1px solid {color};
                color:{color};
                font-size:12px;
                font-weight:600;
                padding:3px 12px;
                border-radius:20px;
            ">
                🏆 Run #{winner_id} &nbsp;
                <span style="font-weight:400; color:#94A3B8;">
                    {winner_val:.1f}
                </span>
            </span>
        </div>
        """

    st.markdown(f"""
    <div style="
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        overflow:hidden;
        margin-bottom:16px;
    ">
        {winners_html}
    </div>
    """, unsafe_allow_html=True)