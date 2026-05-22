"""
simulation_engine/scenario_parser.py

Converts a free-text user prompt into a structured dict of EV simulation
parameters using Grok (xAI) via the OpenAI-compatible SDK.

Output schema
-------------
{
    "temperature_c":      float,   # ambient temperature in Celsius
    "terrain":            str,     # "flat" | "hilly" | "mountainous" | "urban"
    "traffic":            str,     # "light" | "moderate" | "heavy" | "stop_and_go"
    "driving_style":      str,     # "eco" | "moderate" | "aggressive"
    "charging_mode":      str,     # "none" | "slow" | "fast" | "ultra_fast"
    "charging_frequency": str,     # "none" | "once" | "twice" | "frequent"
    "weather":            str,     # "clear" | "rain" | "snow" | "fog"
    "initial_battery_pct":float,   # starting battery percentage 0–100
    "trip_distance_km":   float,   # estimated trip distance
    "humidity_pct":       float,   # relative humidity 0–100
}
"""

import json
import re
from openai import OpenAI

from config import XAI_API_KEY, XAI_BASE_URL, GROK_MODEL


# ─────────────────────────────────────────────────────────────────────────────
# Grok client (singleton)
# ─────────────────────────────────────────────────────────────────────────────

_client = OpenAI(
    api_key=XAI_API_KEY,
    base_url=XAI_BASE_URL,
)


# ─────────────────────────────────────────────────────────────────────────────
# System prompt
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """
You are an EV simulation parameter extractor.

The user will describe an electric vehicle scenario in natural language.
Your job is to extract structured simulation parameters from that description
and return them as a single valid JSON object — nothing else, no explanation,
no markdown, no code fences.

Rules:
- Always return exactly the keys listed below, no extras.
- If a value is not mentioned, infer a sensible default.
- All numeric values must be numbers, not strings.
- "terrain" must be one of: flat, hilly, mountainous, urban
- "traffic" must be one of: light, moderate, heavy, stop_and_go
- "driving_style" must be one of: eco, moderate, aggressive
- "charging_mode" must be one of: none, slow, fast, ultra_fast
- "charging_frequency" must be one of: none, once, twice, frequent
- "weather" must be one of: clear, rain, snow, fog

Required JSON keys:
{
  "temperature_c": <float, e.g. 42.0>,
  "terrain": <string>,
  "traffic": <string>,
  "driving_style": <string>,
  "charging_mode": <string>,
  "charging_frequency": <string>,
  "weather": <string>,
  "initial_battery_pct": <float, 0-100>,
  "trip_distance_km": <float>,
  "humidity_pct": <float, 0-100>
}
""".strip()


# ─────────────────────────────────────────────────────────────────────────────
# Defaults (fallback if parsing fails)
# ─────────────────────────────────────────────────────────────────────────────

_DEFAULTS: dict = {
    "temperature_c": 25.0,
    "terrain": "urban",
    "traffic": "moderate",
    "driving_style": "moderate",
    "charging_mode": "fast",
    "charging_frequency": "once",
    "weather": "clear",
    "initial_battery_pct": 100.0,
    "trip_distance_km": 60.0,
    "humidity_pct": 50.0,
}

_VALID = {
    "terrain": {"flat", "hilly", "mountainous", "urban"},
    "traffic": {"light", "moderate", "heavy", "stop_and_go"},
    "driving_style": {"eco", "moderate", "aggressive"},
    "charging_mode": {"none", "slow", "fast", "ultra_fast"},
    "charging_frequency": {"none", "once", "twice", "frequent"},
    "weather": {"clear", "rain", "snow", "fog"},
}


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def parse_scenario(prompt: str) -> dict:
    """
    Send prompt to Grok and return a validated parameter dict.

    Falls back to rule-based defaults if the API call fails or
    returns malformed JSON.

    Parameters
    ----------
    prompt : str
        Raw user input, e.g. "Simulate EV in Delhi summer with fast charging."

    Returns
    -------
    dict  — validated scenario parameters
    """
    try:
        params = _call_grok(prompt)
    except Exception as exc:
        print(f"[scenario_parser] Grok call failed: {exc}. Using rule-based fallback.")
        params = _rule_based_fallback(prompt)

    return _validate(params)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _call_grok(prompt: str) -> dict:
    """Call Grok and parse the JSON response."""
    response = _client.chat.completions.create(
        model=GROK_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.2,       # low temp for deterministic structured output
        max_tokens=512,
    )

    raw: str = response.choices[0].message.content.strip()

    # Strip markdown fences if model wraps anyway
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)

    return json.loads(raw)


def _rule_based_fallback(prompt: str) -> dict:
    """
    Simple keyword-based extractor used when Grok is unavailable.
    Not as smart as the LLM but keeps the app functional offline.
    """
    p = prompt.lower()
    params = dict(_DEFAULTS)

    # Temperature
    if any(w in p for w in ["summer", "hot", "heat", "delhi", "scorching"]):
        params["temperature_c"] = 42.0
        params["humidity_pct"] = 60.0
    elif any(w in p for w in ["cold", "winter", "snow", "freezing", "frost"]):
        params["temperature_c"] = -4.0
        params["humidity_pct"] = 70.0
        params["weather"] = "snow"
    elif any(w in p for w in ["rain", "monsoon", "wet"]):
        params["temperature_c"] = 28.0
        params["humidity_pct"] = 90.0
        params["weather"] = "rain"

    # Terrain
    if any(w in p for w in ["hill", "hilly", "mountain", "slope", "ghat"]):
        params["terrain"] = "hilly"
    elif any(w in p for w in ["highway", "expressway", "motorway"]):
        params["terrain"] = "flat"
    elif any(w in p for w in ["city", "urban", "traffic", "delhi", "mumbai"]):
        params["terrain"] = "urban"

    # Traffic
    if any(w in p for w in ["heavy", "congested", "jam", "rush"]):
        params["traffic"] = "heavy"
    elif any(w in p for w in ["stop", "stop-and-go", "bumper"]):
        params["traffic"] = "stop_and_go"
    elif any(w in p for w in ["highway", "light", "free"]):
        params["traffic"] = "light"

    # Driving style
    if any(w in p for w in ["aggressive", "sport", "fast driving", "rapid"]):
        params["driving_style"] = "aggressive"
    elif any(w in p for w in ["eco", "gentle", "smooth", "efficient"]):
        params["driving_style"] = "eco"

    # Charging
    if any(w in p for w in ["ultra fast", "ultra-fast", "350kw"]):
        params["charging_mode"] = "ultra_fast"
    elif any(w in p for w in ["fast charg", "dc fast", "quick charg"]):
        params["charging_mode"] = "fast"
    elif any(w in p for w in ["slow charg", "ac charg", "overnight"]):
        params["charging_mode"] = "slow"
    elif any(w in p for w in ["no charg", "without charg"]):
        params["charging_mode"] = "none"
        params["charging_frequency"] = "none"

    if any(w in p for w in ["repeated", "frequent", "every hour", "multiple"]):
        params["charging_frequency"] = "frequent"
    elif any(w in p for w in ["twice", "two charg"]):
        params["charging_frequency"] = "twice"
    elif any(w in p for w in ["once", "one charg", "single charg"]):
        params["charging_frequency"] = "once"

    # Distance
    if "100 km" in p or "100km" in p:
        params["trip_distance_km"] = 100.0
    elif "200 km" in p or "200km" in p:
        params["trip_distance_km"] = 200.0
    elif "highway" in p:
        params["trip_distance_km"] = 120.0

    return params


def _validate(params: dict) -> dict:
    """
    Ensure all keys exist, enum fields are valid, and numerics are in range.
    Invalid values are replaced with defaults.
    """
    validated = dict(_DEFAULTS)
    validated.update(params)

    # Enum validation
    for field, valid_set in _VALID.items():
        if validated.get(field) not in valid_set:
            validated[field] = _DEFAULTS[field]

    # Numeric clamps
    validated["temperature_c"]      = float(validated["temperature_c"])
    validated["initial_battery_pct"] = max(10.0, min(100.0, float(validated["initial_battery_pct"])))
    validated["trip_distance_km"]   = max(10.0, min(500.0, float(validated["trip_distance_km"])))
    validated["humidity_pct"]       = max(0.0,  min(100.0, float(validated["humidity_pct"])))

    return validated