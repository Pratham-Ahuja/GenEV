"""
config.py — central settings for GenEV 2.0
All modules import from here; never read os.environ directly elsewhere.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Groq ──────────────────────────────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = "llama-3.3-70b-versatile"

# ── Supabase ──────────────────────────────────────────────────────────────────
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")

# ── App ───────────────────────────────────────────────────────────────────────
APP_TITLE: str = os.getenv("APP_TITLE", "GenEV")
APP_VERSION: str = os.getenv("APP_VERSION", "2.0.0")
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

# Stability score
VOLTAGE_FLUCTUATION_MAX: float = 20.0
THERMAL_FLUCTUATION_MAX: float = 15.0

# ── Subscription limits ───────────────────────────────────────────────────────
FREE_SIMULATIONS_PER_DAY: int  = int(os.getenv("FREE_SIMULATIONS_PER_DAY", 3))
FREE_QUESTIONS_PER_DAY: int    = int(os.getenv("FREE_QUESTIONS_PER_DAY", 1))
PREMIUM_SIMULATIONS_PER_DAY: int = int(os.getenv("PREMIUM_SIMULATIONS_PER_DAY", 999))
PREMIUM_QUESTIONS_PER_DAY: int   = int(os.getenv("PREMIUM_QUESTIONS_PER_DAY", 10))
PREMIUM_PRICE_INR: int           = int(os.getenv("PREMIUM_PRICE_INR", 299))

# ── Subscription feature gates ────────────────────────────────────────────────
FREE_FEATURES = [
    "EV Scenario Simulation",
    "Performance Metrics Dashboard",
    "Telemetry Visualisation",
    "Scenario History",
    "Scenario Comparison",
    f"{FREE_QUESTIONS_PER_DAY} AI Question/day",
]

PREMIUM_FEATURES = [
    "Everything in Free",
    f"{PREMIUM_QUESTIONS_PER_DAY} AI Questions/day",
    "PDF Report Export",
    "Priority AI Responses",
    "Advanced EV Insights",
    "Unlimited Simulations",
]

# ── RAG settings ──────────────────────────────────────────────────────────────
RAG_TOP_K: int          = int(os.getenv("RAG_TOP_K", 4))
RAG_CHUNK_SIZE: int     = int(os.getenv("RAG_CHUNK_SIZE", 500))
RAG_CHUNK_OVERLAP: int  = int(os.getenv("RAG_CHUNK_OVERLAP", 50))
CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "rag/chroma_db")

# ── PDF Export ────────────────────────────────────────────────────────────────
PDF_OUTPUT_DIR: str = os.getenv("PDF_OUTPUT_DIR", "exports")

# ── Creator info ──────────────────────────────────────────────────────────────
CREATOR_NAME: str     = "Pratham Ahuja"
CREATOR_EMAIL: str    = "prathamahuja924@gmail.com"
CREATOR_LINKEDIN: str = "https://www.linkedin.com/in/pratham-ahuja-4b9b6a284/"
CREATOR_GITHUB: str   = "https://github.com/prathamahuja"

# ── Validation on startup ─────────────────────────────────────────────────────
def validate_config() -> list[str]:
    """
    Check all required environment variables are set.
    Returns list of missing keys.
    """
    required = {
        "GROQ_API_KEY":      GROQ_API_KEY,
        "SUPABASE_URL":      SUPABASE_URL,
        "SUPABASE_ANON_KEY": SUPABASE_ANON_KEY,
    }
    return [k for k, v in required.items() if not v]