"""
config.py — central settings for GenEV.
All modules import from here; never read os.environ directly elsewhere.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── xAI / Grok ────────────────────────────────────────────────────────────────
XAI_API_KEY: str = os.getenv("XAI_API_KEY", "")
XAI_BASE_URL: str = "https://api.x.ai/v1"
GROK_MODEL: str = "grok-3"

# ── App ───────────────────────────────────────────────────────────────────────
APP_TITLE: str = os.getenv("APP_TITLE", "GenEV")
APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

# ── Database ──────────────────────────────────────────────────────────────────
DB_PATH: str = os.getenv("DB_PATH", "genev.db")

# ── Simulation ────────────────────────────────────────────────────────────────
SIM_DURATION_MINUTES: int = int(os.getenv("SIM_DURATION_MINUTES", 60))
SIM_TIME_STEP_MINUTES: int = int(os.getenv("SIM_TIME_STEP_MINUTES", 5))
SIM_STEPS: int = SIM_DURATION_MINUTES // SIM_TIME_STEP_MINUTES  # 12 steps

# ── EV physical constants (based on a mid-range 60 kWh EV) ───────────────────
BATTERY_CAPACITY_KWH: float = 60.0       # usable pack capacity
BATTERY_NOMINAL_VOLTAGE: float = 400.0   # nominal pack voltage (V)
MAX_CHARGE_RATE_KW: float = 150.0        # DC fast charge peak power
THERMAL_SAFE_MAX_C: float = 45.0         # upper safe cell temperature
THERMAL_CRITICAL_C: float = 60.0         # thermal runaway risk threshold
REGEN_EFFICIENCY: float = 0.70           # regenerative braking efficiency

# ── Metric thresholds ─────────────────────────────────────────────────────────
EFFICIENCY_BASELINE_KM_KWH: float = 6.0  # ideal condition reference

# Battery Stress Index weights (α β γ δ)
BSI_ALPHA: float = 0.30   # thermal load
BSI_BETA: float  = 0.30   # charging intensity
BSI_GAMMA: float = 0.20   # acceleration stress
BSI_DELTA: float = 0.20   # discharge severity

# Stability score — max allowable fluctuation bands
VOLTAGE_FLUCTUATION_MAX: float = 20.0    # V
THERMAL_FLUCTUATION_MAX: float = 15.0    # °C