"""
config.py — central settings for GenEV.
All modules import from here; never read os.environ directly elsewhere.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Groq ──────────────────────────────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = "llama-3.3-70b-versatile"

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
BATTERY_CAPACITY_KWH: float = 60.0
BATTERY_NOMINAL_VOLTAGE: float = 400.0
MAX_CHARGE_RATE_KW: float = 150.0
THERMAL_SAFE_MAX_C: float = 45.0
THERMAL_CRITICAL_C: float = 60.0
REGEN_EFFICIENCY: float = 0.70

# ── Metric thresholds ─────────────────────────────────────────────────────────
EFFICIENCY_BASELINE_KM_KWH: float = 6.0

# Battery Stress Index weights (α β γ δ)
BSI_ALPHA: float = 0.30
BSI_BETA: float  = 0.30
BSI_GAMMA: float = 0.20
BSI_DELTA: float = 0.20

# Stability score — max allowable fluctuation bands
VOLTAGE_FLUCTUATION_MAX: float = 20.0
THERMAL_FLUCTUATION_MAX: float = 15.0