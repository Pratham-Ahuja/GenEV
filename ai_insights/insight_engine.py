"""
ai_insights/insight_engine.py

Uses Groq (LLaMA 3.3 70B) to generate intelligent natural language
explanations of simulation results.
Falls back to rule-based insights if API is unavailable.

Output
------
List of 5 insight strings explaining:
- What happened in the simulation
- Why it happened (physics/chemistry reasoning)
- How metrics were affected
- What the user should do differently
"""

import json
import re
from groq import Groq

from config import GROQ_API_KEY, GROQ_MODEL


# ─────────────────────────────────────────────────────────────────────────────
# Groq client
# ─────────────────────────────────────────────────────────────────────────────

_client = Groq(api_key=GROQ_API_KEY)


# ─────────────────────────────────────────────────────────────────────────────
# System prompt
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """
You are an expert EV systems engineer and AI analyst for GenEV,
an electric vehicle simulation platform.

You will receive a JSON object containing:
- scenario_label : human-readable description of the scenario
- params         : EV operating conditions
- summary        : aggregated simulation statistics
- metrics        : computed performance metrics with grades
- risk_flags     : list of risk warnings already detected

Your job is to generate exactly 5 insight strings in a JSON array.
Each insight must:
1. Be 1-2 sentences, specific, and data-driven (reference actual numbers)
2. Explain cause and effect using EV physics or electrochemistry reasoning
3. Include a concrete actionable recommendation where relevant
4. Be written for a technically literate audience (engineering student level)

Return ONLY a valid JSON array of 5 strings. No preamble, no markdown,
no explanation outside the array. Example format:
["Insight one.", "Insight two.", ...]

Do not repeat information from risk_flags verbatim — add deeper analysis.
""".strip()


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def generate_insights(
    simulation_result: dict,
    metrics: dict,
) -> list[str]:
    """
    Generate AI-powered insight strings from simulation results.

    Parameters
    ----------
    simulation_result : dict
        Output of simulator.run_simulation()
    metrics : dict
        Output of metrics.compute_metrics()

    Returns
    -------
    list[str] — 5 insight strings
    """
    try:
        insights = _call_groq(simulation_result, metrics)
    except Exception as exc:
        print(f"[insight_engine] Groq call failed: {exc}. Using rule-based fallback.")
        insights = _rule_based_insights(simulation_result, metrics)

    # Sanitise — ensure we always return exactly 5 strings
    insights = [str(i).strip() for i in insights if str(i).strip()]
    if len(insights) < 5:
        insights += _rule_based_insights(simulation_result, metrics)
    return insights[:5]


# ─────────────────────────────────────────────────────────────────────────────
# Groq call
# ─────────────────────────────────────────────────────────────────────────────

def _call_groq(simulation_result: dict, metrics: dict) -> list[str]:
    """Build the payload and call Groq LLaMA."""

    # Compact context — avoid sending full telemetry (too large)
    context = {
        "scenario_label": simulation_result["scenario_label"],
        "params":         simulation_result["params"],
        "summary":        simulation_result["summary"],
        "metrics": {
            "efficiency_score":     metrics["efficiency_score"],
            "battery_stress_index": metrics["battery_stress_index"],
            "thermal_risk_pct":     metrics["thermal_risk_pct"],
            "stability_score":      metrics["stability_score"],
            "charging_efficiency":  metrics["charging_efficiency"],
            "ai_optimization_gain": metrics["ai_optimization_gain"],
            "overall_score":        metrics["overall_score"],
            "grades":               metrics["grades"],
        },
        "risk_flags": metrics["risk_flags"],
    }

    response = _client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": json.dumps(context, indent=2)},
        ],
        temperature=0.5,
        max_tokens=1024,
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown fences if model wraps anyway
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$",       "", raw)

    return json.loads(raw)


# ─────────────────────────────────────────────────────────────────────────────
# Rule-based fallback
# ─────────────────────────────────────────────────────────────────────────────

def _rule_based_insights(
    simulation_result: dict,
    metrics: dict,
) -> list[str]:
    """
    Generate deterministic insights from metric values when Groq
    is unavailable. Covers all major scenario conditions.
    """
    summary = simulation_result["summary"]
    params  = simulation_result["params"]
    m       = metrics

    insights = []

    # ── Insight 1 — Efficiency ────────────────────────────────────────────────
    eff   = m["efficiency_score"]
    dist  = summary["total_distance_km"]
    enrg  = summary["total_energy_kwh"]
    km_kw = round(dist / enrg, 2) if enrg > 0 else 0

    if eff >= 75:
        insights.append(
            f"Energy efficiency is strong at {eff:.1f}/100 ({km_kw} km/kWh) — "
            f"the {params['driving_style']} driving style and {params['terrain']} terrain "
            f"allowed near-optimal energy utilisation across the {dist:.1f} km trip."
        )
    elif eff >= 50:
        insights.append(
            f"Energy efficiency scored {eff:.1f}/100 ({km_kw} km/kWh), below the "
            f"{6.0} km/kWh ideal baseline — {params['terrain']} terrain and "
            f"{params['traffic'].replace('_',' ')} traffic conditions increased "
            f"rolling resistance and stop-start losses significantly."
        )
    else:
        insights.append(
            f"Poor energy efficiency ({eff:.1f}/100, {km_kw} km/kWh) — "
            f"aggressive discharge under {params['temperature_c']}°C ambient conditions "
            f"compounded with {params['traffic'].replace('_',' ')} traffic caused "
            f"energy consumption well above baseline. Pre-conditioning the cabin and "
            f"battery before departure could recover 8-12% efficiency."
        )

    # ── Insight 2 — Thermal ───────────────────────────────────────────────────
    max_t  = summary["max_temp_c"]
    avg_t  = summary["avg_temp_c"]
    t_risk = m["thermal_risk_pct"]

    if t_risk >= 65:
        insights.append(
            f"Thermal risk reached {t_risk:.1f}% with peak cell temperature of {max_t:.1f}°C — "
            f"at {params['temperature_c']}°C ambient, the battery management system's "
            f"cooling capacity was near its limit. Sustained operation above 45°C "
            f"accelerates SEI layer growth, permanently reducing usable capacity."
        )
    elif t_risk >= 35:
        insights.append(
            f"Moderate thermal risk ({t_risk:.1f}%) observed — average temperature of "
            f"{avg_t:.1f}°C remained manageable but peak of {max_t:.1f}°C during "
            f"charging cycles suggests the thermal management system was working hard. "
            f"Increasing inter-charge intervals by 15-20 minutes would reduce peak heat."
        )
    else:
        insights.append(
            f"Thermal performance was excellent — risk probability of {t_risk:.1f}% "
            f"and average temperature of {avg_t:.1f}°C well within safe operating limits. "
            f"The {params['weather']} weather conditions aided passive cooling."
        )

    # ── Insight 3 — Battery stress ────────────────────────────────────────────
    bsi   = m["battery_stress_index"]
    swing = summary["battery_swing_pct"]

    if bsi >= 70:
        insights.append(
            f"Battery stress index of {bsi:.1f}/100 is in the high-risk zone — "
            f"a {swing:.1f}% SoC swing combined with "
            f"{params['charging_mode'].replace('_',' ')} charging "
            f"and {params['driving_style']} acceleration patterns place significant "
            f"mechanical and electrochemical strain on the cell stack. "
            f"Limiting SoC swing to 20-80% would extend pack life by an estimated 30-40%."
        )
    elif bsi >= 45:
        insights.append(
            f"Moderate battery stress index ({bsi:.1f}/100) — the combination of "
            f"{params['charging_frequency']} charging frequency and {swing:.1f}% "
            f"SoC swing is within tolerable bounds but not optimal for longevity. "
            f"Switching to slower charging during non-urgent stops would reduce stress by ~15%."
        )
    else:
        insights.append(
            f"Battery stress index is healthy at {bsi:.1f}/100 — "
            f"the conservative {params['driving_style']} driving style and "
            f"moderate {swing:.1f}% SoC swing kept electrochemical stress well within "
            f"design limits for the battery pack."
        )

    # ── Insight 4 — Stability & Charging ─────────────────────────────────────
    stab    = m["stability_score"]
    chg_eff = m["charging_efficiency"]
    v_std   = summary["voltage_std_v"]

    if stab < 55:
        insights.append(
            f"System stability scored {stab:.1f}/100 with voltage standard deviation of "
            f"{v_std:.1f}V — frequent power spikes from {params['driving_style']} "
            f"acceleration on {params['terrain']} terrain caused inconsistent current "
            f"draw, stressing the battery management system. Smoother throttle inputs "
            f"could reduce voltage fluctuation by an estimated 20-25%."
        )
    else:
        insights.append(
            f"System stability is solid at {stab:.1f}/100 — voltage deviation of "
            f"{v_std:.1f}V indicates consistent power delivery throughout the trip. "
            f"Charging efficiency of {chg_eff:.1f}% suggests "
            f"{'minimal' if chg_eff > 80 else 'moderate'} energy lost as heat "
            f"during charging sessions."
        )

    # ── Insight 5 — AI Optimisation Gain ─────────────────────────────────────
    gain    = m["ai_optimization_gain"]
    overall = m["overall_score"]

    if gain >= 12:
        insights.append(
            f"AI optimisation modelling identifies a potential {gain:.1f}% performance "
            f"improvement over current operation (overall score: {overall:.1f}/100). "
            f"Key levers: intelligent charge scheduling to avoid peak thermal windows, "
            f"predictive route-based energy allocation, and adaptive regenerative "
            f"braking calibration for {params['terrain']} terrain."
        )
    else:
        insights.append(
            f"With an overall score of {overall:.1f}/100, this scenario is already "
            f"operating near-optimally — AI recommendations offer a modest {gain:.1f}% "
            f"improvement potential, primarily through fine-tuning charge timing "
            f"and regenerative braking thresholds for {params['terrain']} terrain conditions."
        )

    return insights