"""
simulation_engine/telemetry_generator.py

Generates realistic synthetic EV telemetry time-series data from
structured scenario parameters.

Two-layer generation strategy
------------------------------
1. Rule-based physics  — deterministic baseline from EV constants
2. Monte Carlo noise   — gaussian perturbations for realism/variability

Output
------
List of dicts, one per time step:
[
    {
        "time_min":      float,
        "speed_kmh":     float,
        "battery_pct":   float,
        "voltage_v":     float,
        "temp_c":        float,
        "current_a":     float,
        "charge_rate_kw":float,
        "regen_kw":      float,
        "is_charging":   bool,
    },
    ...
]
"""

import numpy as np
from typing import List

from config import (
    SIM_STEPS,
    SIM_TIME_STEP_MINUTES,
    BATTERY_CAPACITY_KWH,
    BATTERY_NOMINAL_VOLTAGE,
    MAX_CHARGE_RATE_KW,
    THERMAL_SAFE_MAX_C,
    THERMAL_CRITICAL_C,
    REGEN_EFFICIENCY,
)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def generate_telemetry(params: dict, seed: int = 42) -> List[dict]:
    """
    Generate synthetic EV telemetry from scenario parameters.

    Parameters
    ----------
    params : dict
        Validated scenario parameters from scenario_parser.parse_scenario()
    seed : int
        Random seed for reproducibility

    Returns
    -------
    List[dict] — one dict per simulation time step
    """
    rng = np.random.default_rng(seed)

    # ── Derive per-scenario modifiers ─────────────────────────────────────────
    mods = _compute_modifiers(params)

    # ── Generate base profiles ────────────────────────────────────────────────
    speed_profile    = _generate_speed_profile(params, mods, rng)
    charging_events  = _generate_charging_schedule(params, mods)
    battery_profile  = _generate_battery_profile(params, mods, speed_profile, charging_events, rng)
    thermal_profile  = _generate_thermal_profile(params, mods, speed_profile, charging_events, battery_profile, rng)
    voltage_profile  = _generate_voltage_profile(battery_profile, thermal_profile, rng)
    current_profile  = _generate_current_profile(speed_profile, charging_events, mods, rng)
    regen_profile    = _generate_regen_profile(speed_profile, params, rng)
    charge_rate_profile = _generate_charge_rate_profile(params, charging_events, thermal_profile)

    # ── Assemble rows ─────────────────────────────────────────────────────────
    telemetry = []
    for i in range(SIM_STEPS):
        telemetry.append({
            "time_min":       round(i * SIM_TIME_STEP_MINUTES, 1),
            "speed_kmh":      round(float(speed_profile[i]), 2),
            "battery_pct":    round(float(np.clip(battery_profile[i], 0, 100)), 2),
            "voltage_v":      round(float(voltage_profile[i]), 2),
            "temp_c":         round(float(thermal_profile[i]), 2),
            "current_a":      round(float(current_profile[i]), 2),
            "charge_rate_kw": round(float(charge_rate_profile[i]), 2),
            "regen_kw":       round(float(regen_profile[i]), 2),
            "is_charging":    bool(charging_events[i]),
        })

    return telemetry


# ─────────────────────────────────────────────────────────────────────────────
# Modifier computation
# ─────────────────────────────────────────────────────────────────────────────

def _compute_modifiers(params: dict) -> dict:
    """
    Convert categorical scenario params into numeric multipliers
    used across all profile generators.
    """
    # Discharge rate modifier (higher = faster drain)
    discharge_mod = 1.0

    # Terrain
    terrain_drain = {"flat": 0.85, "urban": 1.0, "hilly": 1.30, "mountainous": 1.55}
    discharge_mod *= terrain_drain.get(params["terrain"], 1.0)

    # Driving style
    style_drain = {"eco": 0.75, "moderate": 1.0, "aggressive": 1.40}
    discharge_mod *= style_drain.get(params["driving_style"], 1.0)

    # Traffic
    traffic_drain = {"light": 0.85, "moderate": 1.0, "heavy": 1.15, "stop_and_go": 1.25}
    discharge_mod *= traffic_drain.get(params["traffic"], 1.0)

    # Temperature effect on battery (Arrhenius-inspired)
    temp = params["temperature_c"]
    if temp > 35:
        temp_drain = 1.0 + (temp - 35) * 0.012     # heat degrades efficiency
        temp_heat  = 1.0 + (temp - 35) * 0.018     # heat accelerates thermal rise
    elif temp < 5:
        temp_drain = 1.0 + (5 - temp) * 0.020      # cold reduces capacity
        temp_heat  = 0.85                            # cold slows thermal rise
    else:
        temp_drain = 1.0
        temp_heat  = 1.0

    discharge_mod *= temp_drain

    # Weather
    weather_drain = {"clear": 1.0, "rain": 1.08, "snow": 1.20, "fog": 1.05}
    discharge_mod *= weather_drain.get(params["weather"], 1.0)

    # Speed baseline (kmh) by driving style + terrain
    base_speed = {
        ("eco",        "flat"):        80.0,
        ("eco",        "urban"):       35.0,
        ("eco",        "hilly"):       55.0,
        ("eco",        "mountainous"): 40.0,
        ("moderate",   "flat"):        95.0,
        ("moderate",   "urban"):       45.0,
        ("moderate",   "hilly"):       65.0,
        ("moderate",   "mountainous"): 50.0,
        ("aggressive", "flat"):       115.0,
        ("aggressive", "urban"):       60.0,
        ("aggressive", "hilly"):       80.0,
        ("aggressive", "mountainous"): 65.0,
    }.get((params["driving_style"], params["terrain"]), 60.0)

    # Traffic reduces speed
    traffic_speed_factor = {"light": 1.0, "moderate": 0.85, "heavy": 0.65, "stop_and_go": 0.40}
    base_speed *= traffic_speed_factor.get(params["traffic"], 1.0)

    # Charging power
    charge_power = {"none": 0, "slow": 7.4, "fast": 50.0, "ultra_fast": 150.0}

    # How many steps involve charging
    charge_freq_steps = {"none": 0, "once": 1, "twice": 2, "frequent": 4}

    return {
        "discharge_mod":    discharge_mod,
        "temp_heat_mod":    temp_heat,
        "base_speed_kmh":   base_speed,
        "charge_power_kw":  charge_power.get(params["charging_mode"], 0),
        "charge_steps":     charge_freq_steps.get(params["charging_frequency"], 0),
        "ambient_temp":     params["temperature_c"],
        "humidity":         params["humidity_pct"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Profile generators
# ─────────────────────────────────────────────────────────────────────────────

def _generate_speed_profile(params: dict, mods: dict, rng: np.random.Generator) -> np.ndarray:
    """Realistic speed curve with acceleration, cruise, and braking phases."""
    base   = mods["base_speed_kmh"]
    noise  = rng.normal(0, base * 0.08, SIM_STEPS)   # 8% gaussian noise

    # Sinusoidal variation to simulate real driving rhythm
    t      = np.linspace(0, 2 * np.pi, SIM_STEPS)
    wave   = base * 0.15 * np.sin(t * 2.5 + rng.uniform(0, np.pi))

    speed  = base + wave + noise

    # Stop-and-go: random zero-speed events
    if params["traffic"] == "stop_and_go":
        stop_indices = rng.choice(SIM_STEPS, size=SIM_STEPS // 4, replace=False)
        speed[stop_indices] = rng.uniform(0, 5, size=len(stop_indices))

    return np.clip(speed, 0, 200)


def _generate_charging_schedule(params: dict, mods: dict) -> np.ndarray:
    """
    Returns a boolean array — True at steps where charging occurs.
    Charging steps are spaced evenly through the simulation.
    """
    schedule = np.zeros(SIM_STEPS, dtype=bool)
    n = mods["charge_steps"]

    if n == 0 or params["charging_mode"] == "none":
        return schedule

    # Space charging events evenly, avoiding first and last step
    positions = np.linspace(2, SIM_STEPS - 2, n, dtype=int)
    for pos in positions:
        # Each charging event lasts 1–2 steps
        schedule[pos] = True
        if pos + 1 < SIM_STEPS:
            schedule[pos + 1] = True

    return schedule


def _generate_battery_profile(
    params: dict,
    mods: dict,
    speed: np.ndarray,
    charging: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Simulate battery state-of-charge using Peukert-inspired discharge model.
    Battery recovers during charging steps.
    """
    battery    = np.zeros(SIM_STEPS)
    battery[0] = params["initial_battery_pct"]

    # Energy per step at base conditions (kWh per time step)
    dt_hours        = SIM_TIME_STEP_MINUTES / 60.0
    base_drain_pct  = (BATTERY_CAPACITY_KWH * 0.18 / BATTERY_CAPACITY_KWH) * 100 * dt_hours

    for i in range(1, SIM_STEPS):
        speed_factor = (speed[i] / 60.0) ** 1.15    # Peukert exponent ~1.15
        drain        = base_drain_pct * mods["discharge_mod"] * speed_factor
        drain       += rng.normal(0, 0.3)            # measurement noise

        if charging[i]:
            # Charging: recover based on charge power
            charge_pct = (mods["charge_power_kw"] * dt_hours / BATTERY_CAPACITY_KWH) * 100
            battery[i] = min(100.0, battery[i - 1] + charge_pct * 0.92)  # 92% charge efficiency
        else:
            battery[i] = battery[i - 1] - abs(drain)

    return np.clip(battery, 0, 100)


def _generate_thermal_profile(
    params: dict,
    mods: dict,
    speed: np.ndarray,
    charging: np.ndarray,
    battery: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Simulate battery thermal evolution.
    Heat sources: ambient, driving load, charging.
    Heat sink: passive cooling (linear dissipation).
    """
    ambient  = mods["ambient_temp"]
    temp     = np.zeros(SIM_STEPS)
    temp[0]  = ambient + rng.uniform(1, 4)   # slight initial self-heating

    dt_hours = SIM_TIME_STEP_MINUTES / 60.0
    cooling_rate = 2.5   # °C per hour passive cooling

    for i in range(1, SIM_STEPS):
        # Heat from driving (proportional to speed and discharge)
        drive_heat   = (speed[i] / 100.0) * 4.5 * mods["temp_heat_mod"] * dt_hours

        # Heat from charging (fast charging generates significant heat)
        charge_heat  = 0.0
        if charging[i]:
            charge_heat = (mods["charge_power_kw"] / MAX_CHARGE_RATE_KW) * 12.0 * dt_hours

        # Humidity increases heat retention
        humidity_mod = 1.0 + (mods["humidity"] - 50) * 0.002

        # Passive cooling toward ambient
        cooling      = cooling_rate * dt_hours * max(0, temp[i - 1] - ambient)

        temp[i] = (
            temp[i - 1]
            + drive_heat * humidity_mod
            + charge_heat
            - cooling
            + rng.normal(0, 0.4)
        )

    return np.clip(temp, -30, 90)


def _generate_voltage_profile(
    battery: np.ndarray,
    temp: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Battery terminal voltage — drops with SoC and extreme temperature.
    Uses a simplified OCV (open circuit voltage) curve.
    """
    # OCV curve: roughly linear between 340V (0%) and 420V (100%)
    ocv     = 340 + (battery / 100.0) * 80.0

    # Temperature derating
    temp_penalty = np.where(temp > 45, (temp - 45) * 0.3, 0.0)
    temp_penalty += np.where(temp < 10, (10 - temp) * 0.5, 0.0)

    voltage = ocv - temp_penalty + rng.normal(0, 1.2, SIM_STEPS)
    return np.clip(voltage, 280, 430)


def _generate_current_profile(
    speed: np.ndarray,
    charging: np.ndarray,
    mods: dict,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Current draw — positive = discharge, negative = charging.
    """
    # Discharge current proportional to speed (P = IV → I = P/V ≈ P/400)
    power_kw = (speed / 100.0) ** 1.2 * 30.0 * mods["discharge_mod"]
    current  = (power_kw * 1000) / BATTERY_NOMINAL_VOLTAGE   # Amps

    # Charging steps: negative current (current flowing in)
    charge_current = (mods["charge_power_kw"] * 1000) / BATTERY_NOMINAL_VOLTAGE
    current[charging] = -charge_current

    current += rng.normal(0, 2.0, SIM_STEPS)
    return current


def _generate_regen_profile(
    speed: np.ndarray,
    params: dict,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Regenerative braking energy recovery.
    Higher on hilly terrain; lower in stop-and-go (too low speed).
    """
    regen = np.zeros(SIM_STEPS)

    terrain_regen = {"flat": 0.6, "urban": 0.8, "hilly": 1.4, "mountainous": 1.8}
    regen_mod = terrain_regen.get(params["terrain"], 1.0)

    for i in range(1, SIM_STEPS):
        delta_speed = speed[i - 1] - speed[i]
        if delta_speed > 5:   # deceleration event
            recovered = (delta_speed / 100.0) * 15.0 * REGEN_EFFICIENCY * regen_mod
            regen[i]  = max(0, recovered + rng.normal(0, 0.3))

    return np.clip(regen, 0, 80)


def _generate_charge_rate_profile(
    params: dict,
    charging: np.ndarray,
    temp: np.ndarray,
) -> np.ndarray:
    """
    Actual charge rate in kW — derated at high temperatures (thermal throttling).
    """
    rate = np.zeros(SIM_STEPS)
    peak = {"none": 0, "slow": 7.4, "fast": 50.0, "ultra_fast": 150.0}
    peak_kw = peak.get(params["charging_mode"], 0)

    for i in range(SIM_STEPS):
        if charging[i]:
            # Thermal throttling above safe max
            if temp[i] > THERMAL_SAFE_MAX_C:
                derate = max(0.3, 1.0 - (temp[i] - THERMAL_SAFE_MAX_C) * 0.04)
            else:
                derate = 1.0
            rate[i] = peak_kw * derate

    return rate