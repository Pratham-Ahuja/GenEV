"""
frontend/components/charts.py

All Plotly chart builders for the GenEV dashboard.

Charts
------
1. battery_chart       — battery % over time with charging events marked
2. thermal_chart       — thermal profile with safe/critical threshold bands
3. speed_chart         — speed curve with driving style context
4. voltage_chart       — voltage profile with stability bands
5. regen_chart         — regenerative braking energy recovery
6. power_chart         — instantaneous power draw over time
7. radar_chart         — metrics spider/radar chart
8. comparison_bar      — side-by-side metric comparison across runs
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import List

from config import THERMAL_SAFE_MAX_C, THERMAL_CRITICAL_C


# ─────────────────────────────────────────────────────────────────────────────
# Shared theme
# ─────────────────────────────────────────────────────────────────────────────

_COLORS = {
    "green":       "#1D9E75",
    "green_light": "#E1F5EE",
    "orange":      "#D85A30",
    "orange_light":"#FDE8DF",
    "blue":        "#2563EB",
    "blue_light":  "#DBEAFE",
    "purple":      "#7C3AED",
    "red":         "#DC2626",
    "yellow":      "#D97706",
    "grey":        "#6B7280",
    "bg":          "#0F1117",
    "bg_card":     "#1A1D27",
    "border":      "#2D3748",
    "text":        "#E2E8F0",
    "text_muted":  "#94A3B8",
}

_LAYOUT_BASE = dict(
    paper_bgcolor = "rgba(0,0,0,0)",
    plot_bgcolor  = "rgba(0,0,0,0)",
    font          = dict(family="Inter, sans-serif", color=_COLORS["text"], size=12),
    margin        = dict(l=10, r=10, t=40, b=10),
    legend        = dict(
        bgcolor     = "rgba(0,0,0,0)",
        bordercolor = _COLORS["border"],
        borderwidth = 1,
        font        = dict(size=11),
    ),
    xaxis = dict(
        gridcolor     = _COLORS["border"],
        zerolinecolor = _COLORS["border"],
        tickfont      = dict(size=10, color=_COLORS["text_muted"]),
    ),
    yaxis = dict(
        gridcolor     = _COLORS["border"],
        zerolinecolor = _COLORS["border"],
        tickfont      = dict(size=10, color=_COLORS["text_muted"]),
    ),
)


def _base_layout(**kwargs) -> dict:
    layout = dict(_LAYOUT_BASE)
    layout.update(kwargs)
    return layout


def _time_labels(telemetry: List[dict]) -> List[str]:
    return [f"{int(r['time_min'])} min" for r in telemetry]


# ─────────────────────────────────────────────────────────────────────────────
# 1. Battery Chart
# ─────────────────────────────────────────────────────────────────────────────

def battery_chart(telemetry: List[dict]) -> go.Figure:
    """
    Battery % over time.
    Charging steps highlighted with green shading.
    Low (25%) and critical (10%) threshold lines shown.
    """
    times       = _time_labels(telemetry)
    battery     = [r["battery_pct"]  for r in telemetry]
    is_charging = [r["is_charging"]  for r in telemetry]

    fig = go.Figure()

    # Charging event shading
    for i, charging in enumerate(is_charging):
        if charging:
            fig.add_vrect(
                x0=times[max(0, i - 1)], x1=times[i],
                fillcolor=_COLORS["green_light"],
                opacity=0.15, layer="below", line_width=0,
            )

    # Battery line
    fig.add_trace(go.Scatter(
        x=times, y=battery,
        mode="lines+markers",
        name="Battery %",
        line=dict(color=_COLORS["green"], width=2.5, shape="spline"),
        marker=dict(size=5, color=_COLORS["green"]),
        fill="tozeroy",
        fillcolor=f"rgba(29,158,117,0.08)",
    ))

    # Low battery threshold
    fig.add_hline(
        y=25, line_dash="dot", line_color=_COLORS["yellow"],
        annotation_text="Low (25%)",
        annotation_font=dict(size=10, color=_COLORS["yellow"]),
        annotation_position="top right",
    )

    # Critical threshold
    fig.add_hline(
        y=10, line_dash="dot", line_color=_COLORS["red"],
        annotation_text="Critical (10%)",
        annotation_font=dict(size=10, color=_COLORS["red"]),
        annotation_position="bottom right",
    )

    fig.update_layout(**_base_layout(
        title=dict(text="🔋 Battery State of Charge", font=dict(size=14)),
        yaxis=dict(
            title="Battery (%)",
            range=[0, 105],
            gridcolor=_COLORS["border"],
            tickfont=dict(size=10, color=_COLORS["text_muted"]),
        ),
        xaxis=dict(
            title="Time",
            gridcolor=_COLORS["border"],
            tickfont=dict(size=10, color=_COLORS["text_muted"]),
        ),
        showlegend=False,
    ))

    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 2. Thermal Chart
# ─────────────────────────────────────────────────────────────────────────────

def thermal_chart(telemetry: List[dict]) -> go.Figure:
    """
    Temperature over time.
    Safe and critical threshold bands rendered as horizontal fills.
    """
    times = _time_labels(telemetry)
    temps = [r["temp_c"] for r in telemetry]

    fig = go.Figure()

    # Safe zone band
    fig.add_hrect(
        y0=0, y1=THERMAL_SAFE_MAX_C,
        fillcolor="rgba(29,158,117,0.05)",
        layer="below", line_width=0,
    )

    # Warning zone band
    fig.add_hrect(
        y0=THERMAL_SAFE_MAX_C, y1=THERMAL_CRITICAL_C,
        fillcolor="rgba(217,90,48,0.08)",
        layer="below", line_width=0,
    )

    # Critical zone band
    fig.add_hrect(
        y0=THERMAL_CRITICAL_C, y1=100,
        fillcolor="rgba(220,38,38,0.10)",
        layer="below", line_width=0,
    )

    # Safe threshold line
    fig.add_hline(
        y=THERMAL_SAFE_MAX_C,
        line_dash="dash", line_color=_COLORS["orange"],
        annotation_text=f"Safe max ({THERMAL_SAFE_MAX_C}°C)",
        annotation_font=dict(size=10, color=_COLORS["orange"]),
        annotation_position="top left",
    )

    # Critical threshold line
    fig.add_hline(
        y=THERMAL_CRITICAL_C,
        line_dash="dash", line_color=_COLORS["red"],
        annotation_text=f"Critical ({THERMAL_CRITICAL_C}°C)",
        annotation_font=dict(size=10, color=_COLORS["red"]),
        annotation_position="top left",
    )

    # Temperature line — colour shifts by zone
    colors_per_point = [
        _COLORS["red"]    if t >= THERMAL_CRITICAL_C else
        _COLORS["orange"] if t >= THERMAL_SAFE_MAX_C  else
        _COLORS["green"]
        for t in temps
    ]

    fig.add_trace(go.Scatter(
        x=times, y=temps,
        mode="lines+markers",
        name="Temperature",
        line=dict(color=_COLORS["orange"], width=2.5, shape="spline"),
        marker=dict(size=5, color=colors_per_point),
    ))

    fig.update_layout(**_base_layout(
        title=dict(text="🌡️ Battery Thermal Profile", font=dict(size=14)),
        yaxis=dict(
            title="Temperature (°C)",
            gridcolor=_COLORS["border"],
            tickfont=dict(size=10, color=_COLORS["text_muted"]),
        ),
        xaxis=dict(
            title="Time",
            gridcolor=_COLORS["border"],
            tickfont=dict(size=10, color=_COLORS["text_muted"]),
        ),
        showlegend=False,
    ))

    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 3. Speed Chart
# ─────────────────────────────────────────────────────────────────────────────

def speed_chart(telemetry: List[dict]) -> go.Figure:
    """Speed profile over time with average speed reference line."""
    times  = _time_labels(telemetry)
    speeds = [r["speed_kmh"] for r in telemetry]
    avg    = float(np.mean(speeds))

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=times, y=speeds,
        mode="lines",
        name="Speed",
        line=dict(color=_COLORS["blue"], width=2.5, shape="spline"),
        fill="tozeroy",
        fillcolor="rgba(37,99,235,0.08)",
    ))

    fig.add_hline(
        y=avg, line_dash="dot", line_color=_COLORS["grey"],
        annotation_text=f"Avg {avg:.1f} km/h",
        annotation_font=dict(size=10, color=_COLORS["grey"]),
        annotation_position="top right",
    )

    fig.update_layout(**_base_layout(
        title=dict(text="⚡ Speed Profile", font=dict(size=14)),
        yaxis=dict(
            title="Speed (km/h)",
            gridcolor=_COLORS["border"],
            tickfont=dict(size=10, color=_COLORS["text_muted"]),
        ),
        xaxis=dict(
            title="Time",
            gridcolor=_COLORS["border"],
            tickfont=dict(size=10, color=_COLORS["text_muted"]),
        ),
        showlegend=False,
    ))

    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 4. Voltage Chart
# ─────────────────────────────────────────────────────────────────────────────

def voltage_chart(telemetry: List[dict]) -> go.Figure:
    """Voltage profile with ±1 std dev stability band."""
    times    = _time_labels(telemetry)
    voltages = [r["voltage_v"] for r in telemetry]
    avg_v    = float(np.mean(voltages))
    std_v    = float(np.std(voltages))

    upper = [avg_v + std_v] * len(times)
    lower = [avg_v - std_v] * len(times)

    fig = go.Figure()

    # Stability band
    fig.add_trace(go.Scatter(
        x=times + times[::-1],
        y=upper + lower[::-1],
        fill="toself",
        fillcolor="rgba(124,58,237,0.08)",
        line=dict(color="rgba(0,0,0,0)"),
        name="±1σ band",
        showlegend=True,
    ))

    # Voltage line
    fig.add_trace(go.Scatter(
        x=times, y=voltages,
        mode="lines",
        name="Voltage",
        line=dict(color=_COLORS["purple"], width=2.5, shape="spline"),
    ))

    fig.update_layout(**_base_layout(
        title=dict(text="⚡ Pack Voltage", font=dict(size=14)),
        yaxis=dict(
            title="Voltage (V)",
            gridcolor=_COLORS["border"],
            tickfont=dict(size=10, color=_COLORS["text_muted"]),
        ),
        xaxis=dict(
            title="Time",
            gridcolor=_COLORS["border"],
            tickfont=dict(size=10, color=_COLORS["text_muted"]),
        ),
    ))

    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 5. Regen Chart
# ─────────────────────────────────────────────────────────────────────────────

def regen_chart(telemetry: List[dict]) -> go.Figure:
    """Regenerative braking energy recovery per time step."""
    times = _time_labels(telemetry)
    regen = [r["regen_kw"] for r in telemetry]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=times, y=regen,
        name="Regen (kW)",
        marker=dict(
            color=regen,
            colorscale=[[0, _COLORS["green_light"]], [1, _COLORS["green"]]],
            showscale=False,
        ),
    ))

    fig.update_layout(**_base_layout(
        title=dict(text="♻️ Regenerative Braking Recovery", font=dict(size=14)),
        yaxis=dict(
            title="Power Recovered (kW)",
            gridcolor=_COLORS["border"],
            tickfont=dict(size=10, color=_COLORS["text_muted"]),
        ),
        xaxis=dict(
            title="Time",
            gridcolor=_COLORS["border"],
            tickfont=dict(size=10, color=_COLORS["text_muted"]),
        ),
        showlegend=False,
    ))

    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 6. Power Chart
# ─────────────────────────────────────────────────────────────────────────────

def power_chart(telemetry: List[dict]) -> go.Figure:
    """
    Instantaneous power draw over time.
    Positive = discharge, negative = charging (shown in green).
    """
    times  = _time_labels(telemetry)
    powers = [r["power_kw"] for r in telemetry]

    colors = [
        _COLORS["green"] if p < 0 else _COLORS["orange"]
        for p in powers
    ]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=times, y=powers,
        name="Power (kW)",
        marker_color=colors,
    ))

    fig.add_hline(y=0, line_color=_COLORS["border"], line_width=1)

    fig.update_layout(**_base_layout(
        title=dict(text="⚡ Power Draw (+ discharge / − charging)", font=dict(size=14)),
        yaxis=dict(
            title="Power (kW)",
            gridcolor=_COLORS["border"],
            tickfont=dict(size=10, color=_COLORS["text_muted"]),
        ),
        xaxis=dict(
            title="Time",
            gridcolor=_COLORS["border"],
            tickfont=dict(size=10, color=_COLORS["text_muted"]),
        ),
        showlegend=False,
    ))

    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 7. Radar Chart
# ─────────────────────────────────────────────────────────────────────────────

def radar_chart(metrics: dict) -> go.Figure:
    """
    Spider/radar chart of all 5 primary metrics.
    Stress and thermal risk are inverted so that outward = better.
    """
    categories = [
        "Efficiency",
        "Low Stress",
        "Thermal Safety",
        "Stability",
        "Charge Efficiency",
    ]

    values = [
        metrics["efficiency_score"],
        100 - metrics["battery_stress_index"],   # invert: lower stress = better
        100 - metrics["thermal_risk_pct"],        # invert: lower risk = better
        metrics["stability_score"],
        metrics["charging_efficiency"],
    ]

    # Close the polygon
    categories_closed = categories + [categories[0]]
    values_closed     = values     + [values[0]]

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=categories_closed,
        fill="toself",
        fillcolor="rgba(29,158,117,0.15)",
        line=dict(color=_COLORS["green"], width=2),
        name="Score",
    ))

    # Reference: perfect score
    perfect = [100] * (len(categories) + 1)
    fig.add_trace(go.Scatterpolar(
        r=perfect,
        theta=categories_closed,
        fill="toself",
        fillcolor="rgba(255,255,255,0.02)",
        line=dict(color=_COLORS["border"], width=1, dash="dot"),
        name="Perfect",
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=_COLORS["text"], size=11),
        margin=dict(l=30, r=30, t=50, b=30),
        title=dict(text="📊 Performance Radar", font=dict(size=14)),
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                gridcolor=_COLORS["border"],
                tickfont=dict(size=9, color=_COLORS["text_muted"]),
                tickvals=[20, 40, 60, 80, 100],
            ),
            angularaxis=dict(
                gridcolor=_COLORS["border"],
                tickfont=dict(size=11, color=_COLORS["text"]),
            ),
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=10),
        ),
    )

    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 8. Comparison Bar Chart
# ─────────────────────────────────────────────────────────────────────────────

def comparison_bar_chart(runs: List[dict]) -> go.Figure:
    """
    Grouped bar chart comparing key metrics across multiple saved runs.

    Parameters
    ----------
    runs : List[dict]
        Each dict must have keys: scenario_label, metrics
    """
    if not runs:
        fig = go.Figure()
        fig.update_layout(**_base_layout(
            title=dict(text="No runs to compare yet", font=dict(size=14))
        ))
        return fig

    metric_keys = [
        ("efficiency_score",     "Efficiency",      True),
        ("battery_stress_index", "Stress (inv)",    False),
        ("thermal_risk_pct",     "Thermal (inv)",   False),
        ("stability_score",      "Stability",       True),
        ("charging_efficiency",  "Charging Eff.",   True),
    ]

    labels  = [r.get("scenario_label", f"Run {r.get('id','?')}") for r in runs]
    colors  = [
        _COLORS["green"], _COLORS["blue"],
        _COLORS["purple"], _COLORS["orange"], _COLORS["red"],
    ]

    fig = go.Figure()

    for i, run in enumerate(runs):
        m = run.get("metrics", {})
        y_vals = []
        for key, _, higher_better in metric_keys:
            raw = m.get(key, 0)
            # Invert metrics where lower = better for fair visual comparison
            y_vals.append(100 - raw if not higher_better else raw)

        fig.add_trace(go.Bar(
            name=labels[i][:35],   # truncate long labels
            x=[mk[1] for mk in metric_keys],
            y=y_vals,
            marker_color=colors[i % len(colors)],
            opacity=0.85,
        ))

    fig.update_layout(**_base_layout(
        title=dict(text="📊 Scenario Comparison", font=dict(size=14)),
        barmode="group",
        yaxis=dict(
            title="Score (0–100, higher = better)",
            range=[0, 105],
            gridcolor=_COLORS["border"],
            tickfont=dict(size=10, color=_COLORS["text_muted"]),
        ),
        xaxis=dict(
            gridcolor=_COLORS["border"],
            tickfont=dict(size=11, color=_COLORS["text"]),
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=10),
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    ))

    return fig