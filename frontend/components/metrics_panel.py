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
    v = value if higher_is_better else (100 - value)
    if v >= 75: return "#1D9E75"
    if v >= 50: return "#D97706"
    return "#DC2626"


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
    """Render 6 KPI scorecards in a 3-column grid."""
    cards = [
        {
            "label":         "⚡ Efficiency Score",
            "value":         metrics["efficiency_score"],
            "unit":          "/100",
            "higher_better": True,
            "grade":         metrics["grades"]["efficiency"],
            "help":          "Distance per unit energy consumed. Higher = better.",
        },
        {
            "label":         "🔋 Battery Stress Index",
            "value":         metrics["battery_stress_index"],
            "unit":          "/100",
            "higher_better": False,
            "grade":         metrics["grades"]["stress"],
            "help":          "Composite electrochemical stress on the pack. Lower = better.",
        },
        {
            "label":         "🌡️ Thermal Risk",
            "value":         metrics["thermal_risk_pct"],
            "unit":          "%",
            "higher_better": False,
            "grade":         metrics["grades"]["thermal"],
            "help":          "Probability of a thermal event occurring. Lower = better.",
        },
        {
            "label":         "📊 Stability Score",
            "value":         metrics["stability_score"],
            "unit":          "/100",
            "higher_better": True,
            "grade":         metrics["grades"]["stability"],
            "help":          "Voltage and thermal consistency. Higher = better.",
        },
        {
            "label":         "🔌 Charging Efficiency",
            "value":         metrics["charging_efficiency"],
            "unit":          "%",
            "higher_better": True,
            "grade":         metrics["grades"]["charging"],
            "help":          "Energy stored vs energy supplied during charging. Higher = better.",
        },
        {
            "label":         "🤖 AI Optimisation Gain",
            "value":         metrics["ai_optimization_gain"],
            "unit":          "%",
            "higher_better": True,
            "grade":         None,
            "help":          "Estimated performance uplift from AI recommendations.",
        },
    ]

    col1, col2, col3 = st.columns(3)
    columns = [col1, col2, col3, col1, col2, col3]

    for col, card in zip(columns, cards):
        with col:
            color = _score_color(card["value"], card["higher_better"])
            grade = card["grade"]

            st.markdown(
                f'<div style="background:rgba(0,0,0,0.03);border:1px solid '
                f'rgba(0,0,0,0.08);border-radius:12px;padding:16px 18px;margin-bottom:4px;">'
                f'<div style="font-size:13px;color:#0A0A0A;margin-bottom:8px;">{card["label"]}</div>'
                f'<div style="font-size:28px;font-weight:700;color:{color};">'
                f'{card["value"]:.1f}'
                f'<span style="font-size:14px;font-weight:400;color:#475569;margin-left:4px;">'
                f'{card["unit"]}</span></div>'
                f'<div style="margin-top:8px;font-size:11px;color:#475569;">{card["help"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            if grade:
                g_color = _grade_color(grade)
                g_bg    = _grade_bg(grade)
                st.markdown(
                    f'<div style="margin-top:0px;margin-bottom:12px;padding:0 4px;">'
                    f'<span style="background:{g_bg};color:{g_color};font-size:12px;'
                    f'font-weight:600;padding:3px 12px;border-radius:20px;">'
                    f'Grade {grade}</span></div>',
                    unsafe_allow_html=True,
                )


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
        grade = grades.get(key, "—")
        color = _grade_color(grade)
        bg    = _grade_bg(grade)
        badges_html += (
            f'<span style="display:inline-flex;flex-direction:column;align-items:center;'
            f'background:{bg};color:{color};border-radius:10px;padding:6px 14px;'
            f'margin-right:8px;margin-bottom:8px;font-weight:700;font-size:18px;min-width:60px;">'
            f'{grade}'
            f'<span style="font-size:10px;font-weight:400;margin-top:2px;color:{color};">{label}</span>'
            f'</span>'
        )

    st.markdown("**📋 Performance Grades**")
    st.markdown(
        f'<div style="display:flex;flex-wrap:wrap;gap:4px;padding:14px;'
        f'background:rgba(0,0,0,0.03);border:1px solid rgba(0,0,0,0.08);'
        f'border-radius:12px;margin-bottom:16px;">'
        f'{badges_html}</div>',
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
            bg     = "rgba(220,38,38,0.08)"
            border = "#DC2626"
        elif flag.startswith("⚠️"):
            bg     = "rgba(217,119,6,0.08)"
            border = "#D97706"
        else:
            bg     = "rgba(29,158,117,0.08)"
            border = "#1D9E75"

        st.markdown(
            f'<div style="background:{bg};border-left:3px solid {border};'
            f'border-radius:6px;padding:10px 14px;margin-bottom:8px;'
            f'font-size:13px;color:#0A0A0A;line-height:1.5;">'
            f'{flag}</div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Overall Score
# ─────────────────────────────────────────────────────────────────────────────

def render_overall_score(metrics: dict, scenario_label: str) -> None:
    """Large composite score display at the top of the results panel."""
    score = metrics["overall_score"]
    grade = metrics["grades"]["overall"]
    color = _score_color(score, higher_is_better=True)
    g_col = _grade_color(grade)
    g_bg  = _grade_bg(grade)

    st.markdown(
        f'<div style="background:rgba(0,0,0,0.03);border:1px solid rgba(0,0,0,0.08);'
        f'border-radius:16px;padding:24px;text-align:center;margin-bottom:20px;">'
        f'<div style="font-size:12px;color:#0A0A0A;margin-bottom:8px;'
        f'letter-spacing:0.08em;font-weight:600;">OVERALL SCORE</div>'
        f'<div style="font-size:56px;font-weight:700;color:{color};'
        f'line-height:1;margin-bottom:8px;">{score:.1f}</div>'
        f'<div style="font-size:14px;color:#475569;margin-bottom:12px;">/ 100</div>'
        f'<span style="background:{g_bg};color:{g_col};font-size:13px;'
        f'font-weight:600;padding:4px 16px;border-radius:20px;">Grade {grade}</span>'
        f'<div style="font-size:12px;color:#475569;margin-top:14px;'
        f'font-style:italic;">{scenario_label}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


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

    rows_html = ""
    for i, (label, value) in enumerate(rows):
        bg        = "#F8FAFC" if i % 2 == 0 else "#FFFFFF"
        val_color = "#0A0A0A"

        if "Critical" in label and value != "0":
            val_color = "#DC2626"
        elif "Warning" in label and value.isdigit() and int(value) > 2:
            val_color = "#D97706"

        rows_html += (
            f"<tr style='background:{bg};'>"
            f"<td style='padding:8px 12px;font-size:12px;color:#475569;"
            f"border-bottom:1px solid #E2E8F0;'>{label}</td>"
            f"<td style='padding:8px 12px;font-size:13px;font-weight:500;"
            f"color:{val_color};text-align:right;"
            f"border-bottom:1px solid #E2E8F0;'>{value}</td>"
            f"</tr>"
        )

    st.markdown(
        f"<div style='border:1px solid #E2E8F0;border-radius:12px;"
        f"overflow:hidden;margin-bottom:16px;'>"
        f"<table style='width:100%;border-collapse:collapse;'>"
        f"{rows_html}"
        f"</table></div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6. AI Gain Banner
# ─────────────────────────────────────────────────────────────────────────────

def render_ai_gain_banner(metrics: dict) -> None:
    """Highlighted callout showing AI optimisation potential."""
    gain    = metrics["ai_optimization_gain"]
    overall = metrics["overall_score"]

    if gain >= 12:
        icon    = "🚀"
        message = (
            f"High optimisation potential detected — AI recommendations could "
            f"improve overall performance by <strong>{gain:.1f}%</strong>."
        )
    elif gain >= 6:
        icon    = "💡"
        message = (
            f"Moderate optimisation headroom — AI-driven scheduling and routing "
            f"adjustments could yield a <strong>{gain:.1f}%</strong> performance gain."
        )
    else:
        icon    = "✅"
        message = (
            f"This scenario is already near-optimal. AI fine-tuning offers a "
            f"<strong>{gain:.1f}%</strong> marginal improvement."
        )

    st.markdown(
        f'<div style="background:rgba(29,158,117,0.06);border:1px solid '
        f'rgba(29,158,117,0.25);border-radius:12px;padding:16px 20px;'
        f'margin-bottom:16px;">'
        f'<div style="display:flex;align-items:flex-start;gap:12px;">'
        f'<span style="font-size:24px;line-height:1;">{icon}</span>'
        f'<div>'
        f'<div style="font-size:12px;color:#1D9E75;font-weight:600;'
        f'letter-spacing:0.06em;margin-bottom:4px;">AI OPTIMISATION ANALYSIS</div>'
        f'<div style="font-size:13px;color:#0A0A0A;line-height:1.6;">'
        f'{message} Current overall score: '
        f'<strong style="color:#0A0A0A;">{overall:.1f}/100</strong>.'
        f'</div>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )