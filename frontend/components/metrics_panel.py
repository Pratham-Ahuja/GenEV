"""
frontend/components/metrics_panel.py

Streamlit UI components for displaying GenEV metrics.

Sections
--------
1. render_metric_cards     — 6 KPI scorecards in a grid
2. render_grade_badges     — letter grade pills per metric
3. render_risk_flags       — colour-coded warning/info banners
4. render_overall_score    — large composite score with ring indicator
5. render_summary_stats    — trip summary table (distance, energy, etc.)
6. render_ai_gain_banner   — highlighted AI optimisation gain callout
"""

import streamlit as st
from typing import List


# ─────────────────────────────────────────────────────────────────────────────
# Colour helpers
# ─────────────────────────────────────────────────────────────────────────────

def _score_color(value: float, higher_is_better: bool = True) -> str:
    """Return a hex colour based on score quality."""
    v = value if higher_is_better else (100 - value)
    if v >= 75:  return "#1D9E75"   # green
    if v >= 50:  return "#D97706"   # amber
    return       "#DC2626"          # red


def _grade_color(grade: str) -> str:
    return {
        "A": "#1D9E75",
        "B": "#2563EB",
        "C": "#D97706",
        "D": "#D85A30",
        "F": "#DC2626",
    }.get(grade, "#6B7280")


def _grade_bg(grade: str) -> str:
    return {
        "A": "#E1F5EE",
        "B": "#DBEAFE",
        "C": "#FEF3C7",
        "D": "#FDE8DF",
        "F": "#FEE2E2",
    }.get(grade, "#F3F4F6")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Metric Cards
# ─────────────────────────────────────────────────────────────────────────────

def render_metric_cards(metrics: dict) -> None:
    """
    Render 6 KPI scorecards in a 3-column grid.
    Each card shows: label, value, delta indicator, grade badge.
    """
    cards = [
        {
            "label":           "Efficiency Score",
            "value":           metrics["efficiency_score"],
            "unit":            "/100",
            "higher_better":   True,
            "grade":           metrics["grades"]["efficiency"],
            "icon":            "⚡",
            "help":            "Distance per unit energy consumed. Higher = better.",
        },
        {
            "label":           "Battery Stress Index",
            "value":           metrics["battery_stress_index"],
            "unit":            "/100",
            "higher_better":   False,
            "grade":           metrics["grades"]["stress"],
            "icon":            "🔋",
            "help":            "Composite electrochemical stress on the pack. Lower = better.",
        },
        {
            "label":           "Thermal Risk",
            "value":           metrics["thermal_risk_pct"],
            "unit":            "%",
            "higher_better":   False,
            "grade":           metrics["grades"]["thermal"],
            "icon":            "🌡️",
            "help":            "Probability of a thermal event occurring. Lower = better.",
        },
        {
            "label":           "Stability Score",
            "value":           metrics["stability_score"],
            "unit":            "/100",
            "higher_better":   True,
            "grade":           metrics["grades"]["stability"],
            "icon":            "📊",
            "help":            "Voltage and thermal consistency. Higher = better.",
        },
        {
            "label":           "Charging Efficiency",
            "value":           metrics["charging_efficiency"],
            "unit":            "%",
            "higher_better":   True,
            "grade":           metrics["grades"]["charging"],
            "icon":            "🔌",
            "help":            "Energy stored vs energy supplied during charging. Higher = better.",
        },
        {
            "label":           "AI Optimisation Gain",
            "value":           metrics["ai_optimization_gain"],
            "unit":            "%",
            "higher_better":   True,
            "grade":           None,
            "icon":            "🤖",
            "help":            "Estimated performance uplift from AI recommendations.",
        },
    ]

    col1, col2, col3 = st.columns(3)
    columns = [col1, col2, col3, col1, col2, col3]

    for col, card in zip(columns, cards):
        with col:
            color = _score_color(card["value"], card["higher_better"])
            grade = card["grade"]

            grade_html = ""
            if grade:
                g_color = _grade_color(grade)
                g_bg    = _grade_bg(grade)
                grade_html = f"""
                <span style="
                    background:{g_bg};
                    color:{g_color};
                    font-size:11px;
                    font-weight:600;
                    padding:2px 8px;
                    border-radius:20px;
                    margin-left:6px;
                ">Grade {grade}</span>
                """

            st.markdown(f"""
            <div style="
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 12px;
                padding: 16px 18px;
                margin-bottom: 12px;
            ">
                <div style="font-size:13px; color:#94A3B8; margin-bottom:6px;">
                    {card['icon']} {card['label']}
                </div>
                <div style="display:flex; align-items:baseline; gap:4px;">
                    <span style="font-size:28px; font-weight:600; color:{color};">
                        {card['value']:.1f}
                    </span>
                    <span style="font-size:13px; color:#64748B;">{card['unit']}</span>
                    {grade_html}
                </div>
                <div style="font-size:11px; color:#64748B; margin-top:4px;">
                    {card['help']}
                </div>
            </div>
            """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Grade Badges Row
# ─────────────────────────────────────────────────────────────────────────────

def render_grade_badges(metrics: dict) -> None:
    """Render a compact horizontal row of letter grade pills."""
    grades = metrics["grades"]
    labels = {
        "overall":    "Overall",
        "efficiency": "Efficiency",
        "stress":     "Stress",
        "thermal":    "Thermal",
        "stability":  "Stability",
        "charging":   "Charging",
    }

    badges_html = ""
    for key, label in labels.items():
        grade   = grades.get(key, "—")
        color   = _grade_color(grade)
        bg      = _grade_bg(grade)
        badges_html += f"""<span style="display:inline-flex;flex-direction:column;align-items:center;background:{bg};color:{color};border-radius:10px;padding:6px 14px;margin-right:8px;font-weight:700;font-size:18px;min-width:60px;">{grade}<span style="font-size:10px;font-weight:400;margin-top:2px;color:{color};">{label}</span></span>"""

    st.markdown("**📋 Performance Grades**", unsafe_allow_html=False)
    st.markdown(
        f'<div style="display:flex;flex-wrap:wrap;gap:4px;padding:14px;background:rgba(0,0,0,0.03);border:1px solid rgba(0,0,0,0.08);border-radius:12px;margin-bottom:16px;">{badges_html}</div>',
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────────────────────────────────────
# 3. Risk Flags
# ─────────────────────────────────────────────────────────────────────────────

def render_risk_flags(risk_flags: List[str]) -> None:
    """Render risk warnings as styled banners."""
    if not risk_flags:
        return

    st.markdown("#### ⚑ Risk Flags")

    for flag in risk_flags:
        if flag.startswith("🔴"):
            bg      = "rgba(220,38,38,0.10)"
            border  = "#DC2626"
        elif flag.startswith("⚠️"):
            bg      = "rgba(217,144,48,0.10)"
            border  = "#D97706"
        else:
            bg      = "rgba(29,158,117,0.10)"
            border  = "#1D9E75"

        st.markdown(f"""
        <div style="
            background: {bg};
            border-left: 3px solid {border};
            border-radius: 6px;
            padding: 10px 14px;
            margin-bottom: 8px;
            font-size: 13px;
            color: #E2E8F0;
            line-height: 1.5;
        ">
            {flag}
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Overall Score
# ─────────────────────────────────────────────────────────────────────────────

def render_overall_score(metrics: dict, scenario_label: str) -> None:
    """
    Large composite score display at the top of the results panel.
    Shows overall score, grade, and scenario label.
    """
    score  = metrics["overall_score"]
    grade  = metrics["grades"]["overall"]
    color  = _score_color(score, higher_is_better=True)
    g_col  = _grade_color(grade)
    g_bg   = _grade_bg(grade)

    # Score ring using a simple CSS border trick
    st.markdown(f"""
    <div style="
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        margin-bottom: 20px;
    ">
        <div style="font-size:12px; color:#94A3B8; margin-bottom:8px; letter-spacing:0.08em;">
            OVERALL SCORE
        </div>
        <div style="
            font-size:56px;
            font-weight:700;
            color:{color};
            line-height:1;
            margin-bottom:8px;
        ">
            {score:.1f}
        </div>
        <div style="font-size:14px; color:#64748B; margin-bottom:12px;">/ 100</div>
        <span style="
            background:{g_bg};
            color:{g_col};
            font-size:13px;
            font-weight:600;
            padding:4px 16px;
            border-radius:20px;
        ">
            Grade {grade}
        </span>
        <div style="
            font-size:12px;
            color:#64748B;
            margin-top:14px;
            font-style:italic;
        ">
            {scenario_label}
        </div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Summary Stats Table
# ─────────────────────────────────────────────────────────────────────────────

def render_summary_stats(summary: dict) -> None:
    """Render trip summary statistics in a clean two-column table."""
    st.markdown("#### 📋 Trip Summary")

    rows = [
        ("Total Distance",      f"{summary['total_distance_km']:.2f} km"),
        ("Energy Consumed",     f"{summary['total_energy_kwh']:.3f} kWh"),
        ("Avg Speed",           f"{summary['avg_speed_kmh']:.1f} km/h"),
        ("Max Speed",           f"{summary['max_speed_kmh']:.1f} km/h"),
        ("Avg Temperature",     f"{summary['avg_temp_c']:.1f} °C"),
        ("Peak Temperature",    f"{summary['max_temp_c']:.1f} °C"),
        ("Final Battery",       f"{summary['final_battery_pct']:.1f} %"),
        ("Battery Swing",       f"{summary['battery_swing_pct']:.1f} %"),
        ("Regen Recovered",     f"{summary['total_regen_kwh']:.3f} kWh"),
        ("Regen Recovery",      f"{summary['regen_recovery_pct']:.1f} %"),
        ("Charging Events",     str(summary['charging_events'])),
        ("Energy Charged",      f"{summary['total_charge_kwh']:.3f} kWh"),
        ("Thermal Warnings",    str(summary['thermal_violations'])),
        ("Critical Violations", str(summary['critical_violations'])),
        ("Avg Voltage",         f"{summary['avg_voltage_v']:.1f} V"),
        ("Voltage Std Dev",     f"{summary['voltage_std_v']:.2f} V"),
    ]

    # Render as styled HTML table
    rows_html = ""
    for i, (label, value) in enumerate(rows):
        bg = "rgba(255,255,255,0.02)" if i % 2 == 0 else "transparent"

        # Colour critical values red
        val_color = "#E2E8F0"
        if "Critical" in label and value != "0":
            val_color = "#DC2626"
        elif "Warning" in label and int(value) > 2:
            val_color = "#D97706"

        rows_html += f"""
        <tr style="background:{bg};">
            <td style="
                padding:8px 12px;
                font-size:12px;
                color:#94A3B8;
                border-bottom:1px solid rgba(255,255,255,0.04);
            ">{label}</td>
            <td style="
                padding:8px 12px;
                font-size:13px;
                font-weight:500;
                color:{val_color};
                text-align:right;
                border-bottom:1px solid rgba(255,255,255,0.04);
            ">{value}</td>
        </tr>
        """

    st.markdown(f"""
    <div style="
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        overflow: hidden;
        margin-bottom: 16px;
    ">
        <table style="width:100%; border-collapse:collapse;">
            {rows_html}
        </table>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# 6. AI Gain Banner
# ─────────────────────────────────────────────────────────────────────────────

def render_ai_gain_banner(metrics: dict) -> None:
    """Highlighted callout showing AI optimisation potential."""
    gain    = metrics["ai_optimization_gain"]
    overall = metrics["overall_score"]

    if gain >= 12:
        icon    = "🚀"
        message = f"High optimisation potential detected — AI recommendations could improve overall performance by <strong>{gain:.1f}%</strong>."
    elif gain >= 6:
        icon    = "💡"
        message = f"Moderate optimisation headroom — AI-driven scheduling and routing adjustments could yield a <strong>{gain:.1f}%</strong> performance gain."
    else:
        icon    = "✅"
        message = f"This scenario is already near-optimal. AI fine-tuning offers a <strong>{gain:.1f}%</strong> marginal improvement."

    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, rgba(29,158,117,0.12), rgba(37,99,235,0.08));
        border: 1px solid rgba(29,158,117,0.30);
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 16px;
        display: flex;
        align-items: flex-start;
        gap: 12px;
    ">
        <span style="font-size:24px; line-height:1;">{icon}</span>
        <div>
            <div style="font-size:12px; color:#1D9E75; font-weight:600;
                        letter-spacing:0.06em; margin-bottom:4px;">
                AI OPTIMISATION ANALYSIS
            </div>
            <div style="font-size:13px; color:#CBD5E1; line-height:1.6;">
                {message}
                Current overall score: <strong style="color:#E2E8F0;">{overall:.1f}/100</strong>.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)