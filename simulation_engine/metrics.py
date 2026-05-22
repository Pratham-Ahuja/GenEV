"""
simulation_engine/metrics.py

Computes all 6 GenEV evaluation metrics from simulation results.

Metrics
-------
1. Energy Efficiency Score      (0–100)
2. Battery Stress Index         (0–100)
3. Thermal Risk Probability     (0–100 %)
4. Stability Score              (0–100)
5. Charging Efficiency          (0–100 %)
6. AI Optimization Gain         (% improvement over unoptimised baseline)

Output schema
-------------
{
    "efficiency_score":      float,   # 0–100
    "battery_stress_index":  float,   # 0–100
    "thermal_risk_pct":      float,   # 0–100
    "stability_score":       float,   # 0–100
    "charging_efficiency":   float,   # 0–100
    "ai_optimization_gain":  float,   # % e.g. 13.4
    "grades": {
        "efficiency":  str,           # A / B / C / D / F
        "stress":      str,
        "thermal":     str,
        "stability":   str,
        "charging":    str,
        "overall":     str,
    },
    "risk_flags": List[str],          # human-readable warnings
    "overall_score": float,           # weighted composite 0–100
}
"""

import numpy as np
from typing import List

from config import (
    EFFICIENCY_BASELINE_KM_KWH,
    BSI_ALPHA, BSI_BETA, BSI_GAMMA, BSI_DELTA,
    THERMAL_SAFE_MAX_C, THERMAL_CRITICAL_C,
    VOLTAGE_FLUCTUATION_MAX, THERMAL_FLUCTUATION_MAX,
    MAX_CHARGE_RATE_KW, BATTERY_CAPACITY_KWH,
    SIM_STEPS,
)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def compute_metrics(simulation_result: dict) -> dict:
    """
    Compute all 6 metrics from a simulation result dict.

    Parameters
    ----------
    simulation_result : dict
        Output of simulator.run_simulation()

    Returns
    -------
    dict — all metrics, grades, risk flags, and overall score
    """
    summary  = simulation_result["summary"]
    telemetry = simulation_result["telemetry"]
    params   = simulation_result["params"]

    m1 = _energy_efficiency_score(summary)
    m2 = _battery_stress_index(summary, telemetry, params)
    m3 = _thermal_risk_probability(summary, telemetry)
    m4 = _stability_score(summary, telemetry)
    m5 = _charging_efficiency(summary, params)
    m6 = _ai_optimization_gain(m1, m2, m3, m4, params)

    grades      = _compute_grades(m1, m2, m3, m4, m5)
    risk_flags  = _generate_risk_flags(m1, m2, m3, m4, m5, summary, params)
    overall     = _overall_score(m1, m2, m3, m4, m5)
    overall_grade = _grade(overall, higher_is_better=True)

    return {
        "efficiency_score":     round(m1, 2),
        "battery_stress_index": round(m2, 2),
        "thermal_risk_pct":     round(m3, 2),
        "stability_score":      round(m4, 2),
        "charging_efficiency":  round(m5, 2),
        "ai_optimization_gain": round(m6, 2),
        "grades": {
            "efficiency":  grades["efficiency"],
            "stress":      grades["stress"],
            "thermal":     grades["thermal"],
            "stability":   grades["stability"],
            "charging":    grades["charging"],
            "overall":     overall_grade,
        },
        "risk_flags":    risk_flags,
        "overall_score": round(overall, 2),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Metric 1 — Energy Efficiency Score
# ─────────────────────────────────────────────────────────────────────────────

def _energy_efficiency_score(summary: dict) -> float:
    """
    Measures distance travelled per unit energy consumed.

    Formula
    -------
    raw_efficiency = total_distance_km / total_energy_kwh   (km/kWh)
    score = (raw_efficiency / baseline) × 100  clamped to 0–100

    Baseline = 6.0 km/kWh (ideal flat highway eco driving)
    Regen recovery bonus applied on top.
    """
    dist   = summary["total_distance_km"]
    energy = summary["total_energy_kwh"]

    if energy <= 0 or dist <= 0:
        return 0.0

    raw_efficiency = dist / energy   # km/kWh

    # Normalise against baseline
    score = (raw_efficiency / EFFICIENCY_BASELINE_KM_KWH) * 100.0

    # Regen bonus — up to +8 points
    regen_bonus = min(8.0, summary["regen_recovery_pct"] * 0.15)
    score += regen_bonus

    return float(np.clip(score, 0, 100))


# ─────────────────────────────────────────────────────────────────────────────
# Metric 2 — Battery Stress Index
# ─────────────────────────────────────────────────────────────────────────────

def _battery_stress_index(summary: dict, telemetry: List[dict], params: dict) -> float:
    """
    Composite stress score reflecting operational damage to the battery pack.

    Formula
    -------
    BSI = α·T_norm + β·C_norm + γ·A_norm + δ·D_norm   × 100

    Where
    -----
    T_norm = thermal load factor           (0–1)
    C_norm = charging intensity factor     (0–1)
    A_norm = acceleration stress factor   (0–1)
    D_norm = discharge severity factor    (0–1)
    """
    # T — Thermal load (how far above safe threshold on average)
    avg_temp      = summary["avg_temp_c"]
    temp_excess   = max(0, avg_temp - 20)          # excess above 20°C comfort zone
    T_norm        = np.clip(temp_excess / 40.0, 0, 1)   # 60°C = full stress

    # C — Charging intensity (peak charge rate vs max possible)
    charge_mode_power = {
        "none": 0, "slow": 7.4, "fast": 50.0, "ultra_fast": 150.0
    }
    peak_charge = charge_mode_power.get(params["charging_mode"], 0)
    C_norm      = np.clip(peak_charge / MAX_CHARGE_RATE_KW, 0, 1)

    # Frequency amplifier
    freq_amp = {"none": 0.0, "once": 0.6, "twice": 0.8, "frequent": 1.0}
    C_norm  *= freq_amp.get(params["charging_frequency"], 0.5)

    # A — Acceleration stress (driving style proxy)
    style_stress = {"eco": 0.15, "moderate": 0.45, "aggressive": 0.85}
    A_norm       = style_stress.get(params["driving_style"], 0.45)

    # Terrain amplifier for acceleration stress
    terrain_amp  = {"flat": 0.8, "urban": 1.0, "hilly": 1.2, "mountainous": 1.4}
    A_norm      *= terrain_amp.get(params["terrain"], 1.0)
    A_norm       = np.clip(A_norm, 0, 1)

    # D — Discharge severity (how deeply the battery was drained)
    battery_swing = summary["battery_swing_pct"]
    D_norm        = np.clip(battery_swing / 90.0, 0, 1)   # 90% swing = full stress

    # Weighted sum
    BSI = (BSI_ALPHA * T_norm +
           BSI_BETA  * C_norm +
           BSI_GAMMA * A_norm +
           BSI_DELTA * D_norm) * 100.0

    # Penalty for critical thermal violations
    critical_penalty = summary["critical_violations"] * 2.5
    BSI = np.clip(BSI + critical_penalty, 0, 100)

    return float(BSI)


# ─────────────────────────────────────────────────────────────────────────────
# Metric 3 — Thermal Risk Probability
# ─────────────────────────────────────────────────────────────────────────────

def _thermal_risk_probability(summary: dict, telemetry: List[dict]) -> float:
    """
    Probability (0–100%) of a thermal event occurring.

    Factors
    -------
    - Proportion of time spent above safe threshold
    - Proportion of time spent above critical threshold
    - Maximum temperature reached vs critical ceiling
    - Rate of thermal rise (fastest temperature climb observed)
    """
    n = len(telemetry)
    temps = np.array([r["temp_c"] for r in telemetry])

    # Factor 1: time above safe threshold
    frac_above_safe     = summary["thermal_violations"] / n
    frac_above_critical = summary["critical_violations"] / n

    # Factor 2: peak temperature proximity to critical
    peak_temp   = summary["max_temp_c"]
    temp_factor = np.clip((peak_temp - 30) / (THERMAL_CRITICAL_C - 30), 0, 1)

    # Factor 3: maximum rate of thermal rise (°C per step)
    temp_deltas    = np.diff(temps)
    max_rise_rate  = float(np.max(temp_deltas)) if len(temp_deltas) > 0 else 0.0
    rise_factor    = np.clip(max_rise_rate / 8.0, 0, 1)   # 8°C/step = full risk

    # Weighted combination
    risk = (
        0.30 * frac_above_safe * 100 +
        0.35 * frac_above_critical * 100 +
        0.25 * temp_factor * 100 +
        0.10 * rise_factor * 100
    )

    return float(np.clip(risk, 0, 100))


# ─────────────────────────────────────────────────────────────────────────────
# Metric 4 — Stability Score
# ─────────────────────────────────────────────────────────────────────────────

def _stability_score(summary: dict, telemetry: List[dict]) -> float:
    """
    Measures operational consistency across voltage, thermal, and power.

    Higher score = more stable, predictable, safe system behaviour.

    Formula
    -------
    stability = 100 − penalty

    Penalties come from:
    - Voltage fluctuation (std dev vs max allowable)
    - Thermal fluctuation (std dev vs max allowable)
    - Energy spikes (steps with power > 2× average)
    - Battery status warnings (low / critical steps)
    """
    # Voltage stability penalty (0–40 pts)
    v_std          = summary["voltage_std_v"]
    v_penalty      = np.clip((v_std / VOLTAGE_FLUCTUATION_MAX) * 40, 0, 40)

    # Thermal stability penalty (0–30 pts)
    t_std          = summary["thermal_std_c"]
    t_penalty      = np.clip((t_std / THERMAL_FLUCTUATION_MAX) * 30, 0, 30)

    # Energy spike penalty (0–20 pts)
    powers         = np.array([r["power_kw"] for r in telemetry])
    discharge_pwr  = powers[powers > 0]
    if len(discharge_pwr) > 1:
        avg_pwr    = np.mean(discharge_pwr)
        spikes     = np.sum(discharge_pwr > avg_pwr * 2.0)
        spike_penalty = np.clip((spikes / len(discharge_pwr)) * 20, 0, 20)
    else:
        spike_penalty = 0.0

    # Battery warning penalty (0–10 pts)
    warn_steps     = sum(1 for r in telemetry if r["battery_status"] in ("low", "critical"))
    warn_penalty   = np.clip((warn_steps / len(telemetry)) * 10, 0, 10)

    total_penalty  = v_penalty + t_penalty + spike_penalty + warn_penalty
    stability      = 100.0 - total_penalty

    return float(np.clip(stability, 0, 100))


# ─────────────────────────────────────────────────────────────────────────────
# Metric 5 — Charging Efficiency
# ─────────────────────────────────────────────────────────────────────────────

def _charging_efficiency(summary: dict, params: dict) -> float:
    """
    Measures how effectively energy was stored during charging sessions.

    Formula
    -------
    charging_efficiency = (energy_stored / theoretical_max) × 100

    Deratings applied for:
    - High temperature during charging (thermal throttling)
    - High charging frequency (repeated fast charging degrades efficiency)
    """
    if params["charging_mode"] == "none" or summary["charging_events"] == 0:
        return 100.0   # no charging = no charging loss

    energy_charged = summary["total_charge_kwh"]
    if energy_charged <= 0:
        return 100.0

    # Theoretical max: what we could have charged at peak rate with no losses
    from config import SIM_TIME_STEP_MINUTES
    charge_mode_power = {"slow": 7.4, "fast": 50.0, "ultra_fast": 150.0}
    peak_kw     = charge_mode_power.get(params["charging_mode"], 50.0)
    dt_hours    = SIM_TIME_STEP_MINUTES / 60.0
    theoretical = peak_kw * summary["charging_steps"] * dt_hours

    if theoretical <= 0:
        return 100.0

    raw_efficiency = np.clip(energy_charged / theoretical, 0, 1) * 100.0

    # Thermal derate: if max temp was high, charging was throttled
    if summary["max_temp_c"] > THERMAL_SAFE_MAX_C:
        thermal_derate = (summary["max_temp_c"] - THERMAL_SAFE_MAX_C) * 0.6
        raw_efficiency -= thermal_derate

    # Frequency penalty: repeated fast charging loses more energy as heat
    freq_penalty = {"none": 0, "once": 0, "twice": 3, "frequent": 8}
    raw_efficiency -= freq_penalty.get(params["charging_frequency"], 0)

    return float(np.clip(raw_efficiency, 0, 100))


# ─────────────────────────────────────────────────────────────────────────────
# Metric 6 — AI Optimization Gain
# ─────────────────────────────────────────────────────────────────────────────

def _ai_optimization_gain(
    efficiency: float,
    stress: float,
    thermal_risk: float,
    stability: float,
    params: dict,
) -> float:
    """
    Estimates the performance improvement achievable through AI-driven
    optimisation recommendations vs the current unoptimised scenario.

    Logic
    -----
    The worse the current scenario metrics, the higher the potential gain
    (more room to improve). Gain is capped based on what optimisation
    can realistically achieve for the given scenario type.
    """
    # Inefficiency gap — how far below perfect each metric is
    efficiency_gap  = (100 - efficiency) / 100
    stress_gap      = stress / 100
    thermal_gap     = thermal_risk / 100
    instability_gap = (100 - stability) / 100

    # Weighted potential gain
    raw_gain = (
        0.35 * efficiency_gap  +
        0.25 * stress_gap      +
        0.25 * thermal_gap     +
        0.15 * instability_gap
    ) * 100.0

    # Realistic ceiling: AI can't fix everything
    # Aggressive driving: limited gain (driver behaviour)
    # Eco driving: already near optimal, smaller gain
    style_ceiling = {"eco": 8.0, "moderate": 18.0, "aggressive": 14.0}
    ceiling = style_ceiling.get(params["driving_style"], 15.0)

    # Fast/ultra-fast charging: more room to optimise scheduling
    if params["charging_mode"] in ("fast", "ultra_fast"):
        ceiling += 5.0
    if params["charging_frequency"] == "frequent":
        ceiling += 4.0

    gain = np.clip(raw_gain * 0.35, 2.0, ceiling)   # 0.35 = realism dampener
    return float(gain)


# ─────────────────────────────────────────────────────────────────────────────
# Overall composite score
# ─────────────────────────────────────────────────────────────────────────────

def _overall_score(
    efficiency: float,
    stress: float,
    thermal_risk: float,
    stability: float,
    charging: float,
) -> float:
    """
    Weighted composite score (0–100).
    Stress and thermal risk are inverted (lower = better → higher score).
    """
    return float(np.clip(
        0.25 * efficiency        +
        0.25 * (100 - stress)    +
        0.20 * (100 - thermal_risk) +
        0.20 * stability         +
        0.10 * charging,
        0, 100
    ))


# ─────────────────────────────────────────────────────────────────────────────
# Grading
# ─────────────────────────────────────────────────────────────────────────────

def _grade(value: float, higher_is_better: bool = True) -> str:
    """Convert a 0–100 score to a letter grade."""
    v = value if higher_is_better else (100 - value)
    if v >= 85:   return "A"
    if v >= 70:   return "B"
    if v >= 55:   return "C"
    if v >= 40:   return "D"
    return "F"


def _compute_grades(
    efficiency: float,
    stress: float,
    thermal: float,
    stability: float,
    charging: float,
) -> dict:
    return {
        "efficiency": _grade(efficiency,       higher_is_better=True),
        "stress":     _grade(stress,           higher_is_better=False),
        "thermal":    _grade(thermal,          higher_is_better=False),
        "stability":  _grade(stability,        higher_is_better=True),
        "charging":   _grade(charging,         higher_is_better=True),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Risk flags
# ─────────────────────────────────────────────────────────────────────────────

def _generate_risk_flags(
    efficiency: float,
    stress: float,
    thermal: float,
    stability: float,
    charging: float,
    summary: dict,
    params: dict,
) -> List[str]:
    """Generate human-readable risk warnings based on metric values."""
    flags = []

    if thermal >= 70:
        flags.append(
            f"⚠️ High thermal risk ({thermal:.0f}%) — battery temperature reached "
            f"{summary['max_temp_c']:.1f}°C, approaching runaway threshold."
        )

    if stress >= 75:
        flags.append(
            f"⚠️ Elevated battery stress index ({stress:.0f}) — accelerated "
            f"degradation likely. Consider reducing charge frequency or driving aggression."
        )

    if efficiency < 50:
        flags.append(
            f"⚠️ Low efficiency score ({efficiency:.0f}) — only "
            f"{summary['total_distance_km']:.1f} km on "
            f"{summary['total_energy_kwh']:.1f} kWh consumed."
        )

    if stability < 50:
        flags.append(
            f"⚠️ Poor system stability ({stability:.0f}) — high voltage or "
            f"thermal fluctuations detected across the trip."
        )

    if summary["critical_violations"] > 0:
        flags.append(
            f"🔴 Critical thermal event — {summary['critical_violations']} step(s) "
            f"above {THERMAL_CRITICAL_C}°C. Thermal management system likely overwhelmed."
        )

    if summary["min_battery_pct"] <= 10:
        flags.append(
            f"🔴 Battery critically depleted — reached {summary['min_battery_pct']:.1f}% "
            f"during the trip. Risk of deep discharge damage."
        )

    if params["charging_mode"] == "ultra_fast" and params["charging_frequency"] == "frequent":
        flags.append(
            "⚠️ Ultra-fast charging used frequently — this combination causes significant "
            "long-term capacity fade. Limit to emergency use only."
        )

    if charging < 60:
        flags.append(
            f"⚠️ Charging efficiency is low ({charging:.0f}%) — significant energy "
            f"lost as heat during charging sessions."
        )

    if not flags:
        flags.append("✅ No critical risk flags detected. System operating within safe parameters.")

    return flags