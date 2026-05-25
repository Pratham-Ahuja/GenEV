"""
export/pdf_exporter.py

PDF report generation for GenEV 2.0.
Generates a branded, professional simulation report.

Output
------
A downloadable PDF containing:
- GenEV branded header
- User info + scenario details
- Extracted parameters table
- 6 performance metrics with grades
- Risk flags
- Trip summary statistics
- AI insights
- Footer with timestamp
"""

import os
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from reportlab.platypus.flowables import HRFlowable


# ─────────────────────────────────────────────────────────────────────────────
# Brand colours
# ─────────────────────────────────────────────────────────────────────────────

GREEN       = colors.HexColor("#1D9E75")
GREEN_LIGHT = colors.HexColor("#E1F5EE")
DARK        = colors.HexColor("#1E293B")
GREY        = colors.HexColor("#64748B")
LIGHT_GREY  = colors.HexColor("#F8FAFC")
BORDER      = colors.HexColor("#E2E8F0")
RED         = colors.HexColor("#DC2626")
ORANGE      = colors.HexColor("#D97706")
BLUE        = colors.HexColor("#2563EB")
WHITE       = colors.white


# ─────────────────────────────────────────────────────────────────────────────
# Styles
# ─────────────────────────────────────────────────────────────────────────────

def _build_styles():
    base = getSampleStyleSheet()

    styles = {
        "title": ParagraphStyle(
            "title",
            fontName="Helvetica-Bold",
            fontSize=24,
            textColor=GREEN,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            fontName="Helvetica",
            fontSize=11,
            textColor=GREY,
            alignment=TA_CENTER,
            spaceAfter=2,
        ),
        "section_header": ParagraphStyle(
            "section_header",
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=DARK,
            spaceBefore=14,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=9,
            textColor=DARK,
            spaceAfter=3,
            leading=14,
        ),
        "body_small": ParagraphStyle(
            "body_small",
            fontName="Helvetica",
            fontSize=8,
            textColor=GREY,
            spaceAfter=2,
            leading=12,
        ),
        "label": ParagraphStyle(
            "label",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=GREY,
        ),
        "value": ParagraphStyle(
            "value",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=DARK,
        ),
        "insight": ParagraphStyle(
            "insight",
            fontName="Helvetica",
            fontSize=9,
            textColor=DARK,
            leftIndent=10,
            spaceAfter=6,
            leading=14,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontName="Helvetica",
            fontSize=8,
            textColor=GREY,
            alignment=TA_CENTER,
        ),
        "risk_flag": ParagraphStyle(
            "risk_flag",
            fontName="Helvetica",
            fontSize=9,
            textColor=DARK,
            leftIndent=8,
            spaceAfter=4,
            leading=13,
        ),
    }
    return styles


# ─────────────────────────────────────────────────────────────────────────────
# Grade colour helper
# ─────────────────────────────────────────────────────────────────────────────

def _grade_color(grade: str):
    return {
        "A": GREEN,
        "B": BLUE,
        "C": ORANGE,
        "D": colors.HexColor("#D85A30"),
        "F": RED,
    }.get(grade, GREY)


def _score_color(value: float, higher_better: bool = True):
    v = value if higher_better else (100 - value)
    if v >= 75: return GREEN
    if v >= 50: return ORANGE
    return RED


# ─────────────────────────────────────────────────────────────────────────────
# Section builders
# ─────────────────────────────────────────────────────────────────────────────

def _build_header(styles: dict, user_name: str, prompt: str) -> list:
    """Build branded header section."""
    elements = []

    # Logo + title
    elements.append(Spacer(1, 0.3 * cm))
    elements.append(Paragraph("⚡ GenEV", styles["title"]))
    elements.append(Paragraph(
        "AI-Powered EV Simulation Report",
        styles["subtitle"],
    ))
    elements.append(Spacer(1, 0.2 * cm))
    elements.append(HRFlowable(
        width="100%",
        thickness=2,
        color=GREEN,
        spaceAfter=8,
    ))

    # Report meta
    now = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    meta_data = [
        ["Generated for:", user_name],
        ["Date:",          now],
        ["Scenario:",      prompt[:80] + ("..." if len(prompt) > 80 else "")],
    ]
    meta_table = Table(meta_data, colWidths=[4 * cm, 13 * cm])
    meta_table.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",    (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",   (0, 0), (0, -1), GREY),
        ("TEXTCOLOR",   (1, 0), (1, -1), DARK),
        ("TOPPADDING",  (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 0.3 * cm))

    return elements


def _build_scenario_params(
    styles: dict,
    params: dict,
    scenario_label: str,
) -> list:
    """Build scenario parameters section."""
    elements = []

    elements.append(Paragraph("📋 Scenario Parameters", styles["section_header"]))

    # Scenario label badge
    elements.append(Paragraph(
        f"<b>{scenario_label}</b>",
        styles["body"],
    ))
    elements.append(Spacer(1, 0.2 * cm))

    param_rows = [
        ["Parameter", "Value"],
        ["Temperature",    f"{params.get('temperature_c', 'N/A')}°C"],
        ["Terrain",        params.get("terrain", "N/A").capitalize()],
        ["Traffic",        params.get("traffic", "N/A").replace("_", " ").capitalize()],
        ["Driving Style",  params.get("driving_style", "N/A").capitalize()],
        ["Charging Mode",  params.get("charging_mode", "N/A").replace("_", " ").capitalize()],
        ["Charging Freq.", params.get("charging_frequency", "N/A").capitalize()],
        ["Weather",        params.get("weather", "N/A").capitalize()],
        ["Initial SoC",    f"{params.get('initial_battery_pct', 100):.0f}%"],
        ["Trip Distance",  f"{params.get('trip_distance_km', 'N/A')} km"],
        ["Humidity",       f"{params.get('humidity_pct', 'N/A')}%"],
    ]

    col_widths = [6 * cm, 11 * cm]
    table = Table(param_rows, colWidths=col_widths)
    table.setStyle(TableStyle([
        # Header
        ("BACKGROUND",    (0, 0), (-1, 0), GREEN),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 9),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),

        # Body
        ("FONTNAME",      (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",      (1, 1), (1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -1), 9),
        ("TEXTCOLOR",     (0, 1), (0, -1), GREY),
        ("TEXTCOLOR",     (1, 1), (1, -1), DARK),

        # Alternating rows
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREY]),

        # Grid
        ("GRID",          (0, 0), (-1, -1), 0.5, BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ]))

    elements.append(table)
    return elements


def _build_metrics_section(styles: dict, metrics: dict) -> list:
    """Build performance metrics section with grades."""
    elements = []

    elements.append(Paragraph("📊 Performance Metrics", styles["section_header"]))

    # Overall score highlight
    overall      = metrics.get("overall_score", 0)
    overall_grade = metrics.get("grades", {}).get("overall", "—")
    overall_color = _score_color(overall)

    overall_data = [[
        Paragraph("<b>OVERALL SCORE</b>", ParagraphStyle(
            "os", fontName="Helvetica-Bold", fontSize=9,
            textColor=GREY, alignment=TA_CENTER,
        )),
        Paragraph(
            f'<font color="#{overall_color.hexval()[1:]}">'
            f'<b>{overall:.1f}/100</b></font>',
            ParagraphStyle(
                "osv", fontName="Helvetica-Bold", fontSize=18,
                textColor=overall_color, alignment=TA_CENTER,
            ),
        ),
        Paragraph(f"<b>Grade {overall_grade}</b>", ParagraphStyle(
            "osg", fontName="Helvetica-Bold", fontSize=12,
            textColor=_grade_color(overall_grade), alignment=TA_CENTER,
        )),
    ]]

    overall_table = Table(overall_data, colWidths=[5.67 * cm] * 3)
    overall_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), GREEN_LIGHT),
        ("BOX",           (0, 0), (-1, -1), 1, GREEN),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("ROUNDEDCORNERS", [4]),
    ]))
    elements.append(overall_table)
    elements.append(Spacer(1, 0.3 * cm))

    # Individual metrics table
    metric_defs = [
        ("Efficiency Score",     metrics.get("efficiency_score", 0),     True,  "/100",
         metrics.get("grades", {}).get("efficiency", "—")),
        ("Battery Stress Index", metrics.get("battery_stress_index", 0), False, "/100",
         metrics.get("grades", {}).get("stress", "—")),
        ("Thermal Risk",         metrics.get("thermal_risk_pct", 0),     False, "%",
         metrics.get("grades", {}).get("thermal", "—")),
        ("Stability Score",      metrics.get("stability_score", 0),      True,  "/100",
         metrics.get("grades", {}).get("stability", "—")),
        ("Charging Efficiency",  metrics.get("charging_efficiency", 0),  True,  "%",
         metrics.get("grades", {}).get("charging", "—")),
        ("AI Optimisation Gain", metrics.get("ai_optimization_gain", 0), True,  "%",
         None),
    ]

    metric_rows = [["Metric", "Score", "Grade", "Status"]]
    for name, val, hib, unit, grade in metric_defs:
        score_color  = _score_color(val, hib)
        status = "Good" if (val >= 70 if hib else val <= 30) else \
                 "Fair" if (val >= 50 if hib else val <= 55) else "Poor"
        status_color = GREEN if status == "Good" else \
                       ORANGE if status == "Fair" else RED

        metric_rows.append([
            Paragraph(name, ParagraphStyle(
                "mn", fontName="Helvetica", fontSize=9, textColor=DARK,
            )),
            Paragraph(
                f"<b>{val:.1f}{unit}</b>",
                ParagraphStyle(
                    "mv", fontName="Helvetica-Bold", fontSize=10,
                    textColor=score_color,
                ),
            ),
            Paragraph(
                grade or "—",
                ParagraphStyle(
                    "mg", fontName="Helvetica-Bold", fontSize=10,
                    textColor=_grade_color(grade) if grade else GREY,
                    alignment=TA_CENTER,
                ),
            ),
            Paragraph(
                status,
                ParagraphStyle(
                    "ms", fontName="Helvetica-Bold", fontSize=9,
                    textColor=status_color, alignment=TA_CENTER,
                ),
            ),
        ])

    metrics_table = Table(
        metric_rows,
        colWidths=[7 * cm, 4 * cm, 3 * cm, 3 * cm],
    )
    metrics_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 9),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
        ("GRID",          (0, 0), (-1, -1), 0.5, BORDER),
        ("ALIGN",         (1, 1), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 1), (0, -1), 8),
    ]))

    elements.append(metrics_table)
    return elements


def _build_risk_flags(styles: dict, risk_flags: list[str]) -> list:
    """Build risk flags section."""
    elements = []

    elements.append(Paragraph("⚑ Risk Flags", styles["section_header"]))

    for flag in risk_flags:
        if flag.startswith("🔴"):
            bg_color = colors.HexColor("#FEE2E2")
            border_color = RED
        elif flag.startswith("⚠️"):
            bg_color = colors.HexColor("#FEF3C7")
            border_color = ORANGE
        else:
            bg_color = GREEN_LIGHT
            border_color = GREEN

        # Clean emoji for PDF
        clean_flag = flag.replace("🔴", "[!] ").replace("⚠️", "[!] ").replace("✅", "[✓] ")

        flag_table = Table(
            [[Paragraph(clean_flag, styles["risk_flag"])]],
            colWidths=[17 * cm],
        )
        flag_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), bg_color),
            ("LINESTART",     (0, 0), (0, -1), 3, border_color),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(flag_table)
        elements.append(Spacer(1, 0.1 * cm))

    return elements


def _build_trip_summary(styles: dict, summary: dict) -> list:
    """Build trip summary statistics table."""
    elements = []

    elements.append(Paragraph("🚗 Trip Summary", styles["section_header"]))

    rows = [
        ["Metric", "Value", "Metric", "Value"],
        ["Total Distance",
         f"{summary.get('total_distance_km', 0):.2f} km",
         "Energy Consumed",
         f"{summary.get('total_energy_kwh', 0):.3f} kWh"],
        ["Avg Speed",
         f"{summary.get('avg_speed_kmh', 0):.1f} km/h",
         "Max Speed",
         f"{summary.get('max_speed_kmh', 0):.1f} km/h"],
        ["Avg Temperature",
         f"{summary.get('avg_temp_c', 0):.1f}°C",
         "Peak Temperature",
         f"{summary.get('max_temp_c', 0):.1f}°C"],
        ["Final Battery",
         f"{summary.get('final_battery_pct', 0):.1f}%",
         "Battery Swing",
         f"{summary.get('battery_swing_pct', 0):.1f}%"],
        ["Regen Recovered",
         f"{summary.get('total_regen_kwh', 0):.3f} kWh",
         "Regen Recovery",
         f"{summary.get('regen_recovery_pct', 0):.1f}%"],
        ["Charging Events",
         str(summary.get('charging_events', 0)),
         "Energy Charged",
         f"{summary.get('total_charge_kwh', 0):.3f} kWh"],
        ["Thermal Warnings",
         str(summary.get('thermal_violations', 0)),
         "Critical Violations",
         str(summary.get('critical_violations', 0))],
        ["Avg Voltage",
         f"{summary.get('avg_voltage_v', 0):.1f} V",
         "Voltage Std Dev",
         f"{summary.get('voltage_std_v', 0):.2f} V"],
    ]

    col_widths = [5 * cm, 3.5 * cm, 5 * cm, 3.5 * cm]
    table = Table(rows, colWidths=col_widths)
    table.setStyle(TableStyle([
        # Header row
        ("BACKGROUND",    (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 9),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),

        # Label columns
        ("FONTNAME",      (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",      (2, 1), (2, -1), "Helvetica-Bold"),
        ("TEXTCOLOR",     (0, 1), (0, -1), GREY),
        ("TEXTCOLOR",     (2, 1), (2, -1), GREY),
        ("FONTSIZE",      (0, 1), (-1, -1), 9),

        # Value columns
        ("FONTNAME",      (1, 1), (1, -1), "Helvetica"),
        ("FONTNAME",      (3, 1), (3, -1), "Helvetica"),
        ("TEXTCOLOR",     (1, 1), (1, -1), DARK),
        ("TEXTCOLOR",     (3, 1), (3, -1), DARK),

        # Alternating rows
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREY]),

        # Grid
        ("GRID",          (0, 0), (-1, -1), 0.5, BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ]))

    elements.append(table)
    return elements


def _build_insights_section(styles: dict, insights: list[str]) -> list:
    """Build AI insights section."""
    elements = []

    elements.append(Paragraph("🤖 AI Insights", styles["section_header"]))

    for i, insight in enumerate(insights, 1):
        insight_table = Table(
            [[
                Paragraph(f"<b>{i}</b>", ParagraphStyle(
                    "inum", fontName="Helvetica-Bold", fontSize=11,
                    textColor=WHITE, alignment=TA_CENTER,
                )),
                Paragraph(insight, styles["insight"]),
            ]],
            colWidths=[1 * cm, 16 * cm],
        )
        insight_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (0, 0), GREEN),
            ("BACKGROUND",    (1, 0), (1, 0), GREEN_LIGHT),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (0, 0), 4),
            ("LEFTPADDING",   (1, 0), (1, 0), 10),
            ("BOX",           (0, 0), (-1, -1), 0.5, BORDER),
        ]))
        elements.append(insight_table)
        elements.append(Spacer(1, 0.15 * cm))

    return elements


def _build_footer(styles: dict, user_name: str) -> list:
    """Build report footer."""
    elements = []

    elements.append(Spacer(1, 0.5 * cm))
    elements.append(HRFlowable(
        width="100%",
        thickness=1,
        color=BORDER,
        spaceAfter=6,
    ))

    now = datetime.now().strftime("%B %d, %Y %I:%M %p")
    elements.append(Paragraph(
        f"Generated by GenEV v2.0 · {user_name} · {now} · "
        f"Built by Pratham Ahuja · prathamahuja924@gmail.com",
        styles["footer"],
    ))

    return elements


# ─────────────────────────────────────────────────────────────────────────────
# Main export function
# ─────────────────────────────────────────────────────────────────────────────

def generate_pdf(
    simulation_result: dict,
    metrics: dict,
    insights: list[str],
    user_name: str = "GenEV User",
    prompt: str = "",
) -> bytes:
    """
    Generate a complete PDF simulation report.

    Parameters
    ----------
    simulation_result : dict — output of simulator.run_simulation()
    metrics           : dict — output of metrics.compute_metrics()
    insights          : list — AI insight strings
    user_name         : str  — user's display name
    prompt            : str  — original scenario prompt

    Returns
    -------
    bytes — PDF file as bytes (ready for st.download_button)
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=1.5 * cm,
        bottomMargin=2 * cm,
    )

    styles   = _build_styles()
    params   = simulation_result.get("params", {})
    summary  = simulation_result.get("summary", {})
    label    = simulation_result.get("scenario_label", "EV Simulation")
    risk_flags = metrics.get("risk_flags", [])

    elements = []

    # Build all sections
    elements += _build_header(styles, user_name, prompt)
    elements.append(Spacer(1, 0.3 * cm))

    elements += _build_scenario_params(styles, params, label)
    elements.append(Spacer(1, 0.3 * cm))

    elements += _build_metrics_section(styles, metrics)
    elements.append(Spacer(1, 0.3 * cm))

    if risk_flags:
        elements += _build_risk_flags(styles, risk_flags)
        elements.append(Spacer(1, 0.3 * cm))

    elements += _build_trip_summary(styles, summary)
    elements.append(Spacer(1, 0.3 * cm))

    if insights:
        elements += _build_insights_section(styles, insights)

    elements += _build_footer(styles, user_name)

    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Ensure export directory exists
# ─────────────────────────────────────────────────────────────────────────────

def ensure_export_dir() -> str:
    """Create export directory if it doesn't exist."""
    from config import PDF_OUTPUT_DIR
    os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)
    return PDF_OUTPUT_DIR