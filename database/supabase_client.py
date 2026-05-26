"""
database/supabase_client.py

Supabase connection and all database operations for GenEV 2.0.

Covers
------
- Connection singleton
- Profile operations (create, read, update)
- Simulation run operations (save, fetch, delete)
- Chat history operations (save, fetch, clear)
- Feedback operations (save)
- Usage tracking (simulations + questions per day)
"""

from datetime import date
from typing import Optional
from supabase import create_client, Client

from config import SUPABASE_URL, SUPABASE_ANON_KEY


# ─────────────────────────────────────────────────────────────────────────────
# Connection singleton
# ─────────────────────────────────────────────────────────────────────────────

_client: Optional[Client] = None


def get_client() -> Client:
    """Return a singleton Supabase client."""
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env"
            )
        _client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return _client


def set_auth_token(access_token: str) -> None:
    """
    Inject user's auth token into the client so RLS policies
    apply correctly for that user's session.
    """
    client = get_client()
    client.postgrest.auth(access_token)


# ─────────────────────────────────────────────────────────────────────────────
# Profile cache invalidation
# ─────────────────────────────────────────────────────────────────────────────

def _invalidate_profile_cache() -> None:
    """Clear cached profile from session state so next read is fresh."""
    try:
        import streamlit as st
        if "genev_profile" in st.session_state:
            del st.session_state["genev_profile"]
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Profile operations
# ─────────────────────────────────────────────────────────────────────────────

def create_profile(
    user_id: str,
    name: str,
    email: str,
    city: str = "",
    daily_commute_km: float = 30.0,
    has_home_charging: bool = False,
    driving_style: str = "moderate",
) -> dict:
    """Create a new user profile after signup."""
    client = get_client()
    today  = str(date.today())
    data = {
        "id":                     user_id,
        "name":                   name,
        "email":                  email,
        "city":                   city,
        "daily_commute_km":       daily_commute_km,
        "has_home_charging":      has_home_charging,
        "driving_style":          driving_style,
        "subscription_plan":      "free",
        "simulations_used_today": 0,
        "questions_used_today":   0,
        "usage_reset_date":       today,
    }
    response = client.table("profiles").insert(data).execute()
    return response.data[0] if response.data else {}


def get_profile(user_id: str) -> Optional[dict]:
    """Fetch a user's profile directly from Supabase (never cached)."""
    client = get_client()
    response = (
        client.table("profiles")
        .select("*")
        .eq("id", user_id)
        .execute()
    )
    return response.data[0] if response.data else None


def update_profile(user_id: str, updates: dict) -> dict:
    """Update specific fields of a user profile."""
    client = get_client()
    response = (
        client.table("profiles")
        .update(updates)
        .eq("id", user_id)
        .execute()
    )
    _invalidate_profile_cache()
    return response.data[0] if response.data else {}


# ─────────────────────────────────────────────────────────────────────────────
# Usage tracking
# ─────────────────────────────────────────────────────────────────────────────

def _reset_usage_if_needed(profile: dict) -> dict:
    """
    Reset daily usage counters if the reset date is before today.
    Also fixes profiles that have NULL or missing reset dates.
    """
    today      = str(date.today())
    reset_date = profile.get("usage_reset_date")

    # Normalise — date objects vs strings
    if reset_date and not isinstance(reset_date, str):
        reset_date = str(reset_date)

    if not reset_date or reset_date != today:
        updates = {
            "simulations_used_today": 0,
            "questions_used_today":   0,
            "usage_reset_date":       today,
        }
        try:
            update_profile(profile["id"], updates)
        except Exception as e:
            print(f"[supabase_client] Failed to reset usage: {e}")
        profile = {**profile, **updates}

    return profile


def check_simulation_limit(user_id: str) -> tuple[bool, int, int]:
    """
    Check if user can run another simulation.

    Returns
    -------
    (allowed, used_today, daily_limit)
    """
    from config import FREE_SIMULATIONS_PER_DAY, PREMIUM_SIMULATIONS_PER_DAY

    profile = get_profile(user_id)

    if not profile:
        return True, 0, FREE_SIMULATIONS_PER_DAY

    profile = _reset_usage_if_needed(profile)

    plan  = profile.get("subscription_plan", "free")
    limit = (
        PREMIUM_SIMULATIONS_PER_DAY
        if plan == "premium"
        else FREE_SIMULATIONS_PER_DAY
    )
    used = profile.get("simulations_used_today", 0) or 0

    return used < limit, used, limit


def increment_simulation_count(user_id: str) -> None:
    """
    Increment simulation count for today.
    Always fetches fresh from DB — never uses cache.
    """
    profile = get_profile(user_id)
    if not profile:
        return
    profile = _reset_usage_if_needed(profile)
    used    = profile.get("simulations_used_today", 0) or 0
    update_profile(user_id, {"simulations_used_today": used + 1})
    _invalidate_profile_cache()


def check_question_limit(user_id: str) -> tuple[bool, int, int]:
    """
    Check if user can ask another AI question.

    Returns
    -------
    (allowed, used_today, daily_limit)
    """
    from config import FREE_QUESTIONS_PER_DAY, PREMIUM_QUESTIONS_PER_DAY

    profile = get_profile(user_id)

    if not profile:
        return True, 0, FREE_QUESTIONS_PER_DAY

    profile = _reset_usage_if_needed(profile)

    plan  = profile.get("subscription_plan", "free")
    limit = (
        PREMIUM_QUESTIONS_PER_DAY
        if plan == "premium"
        else FREE_QUESTIONS_PER_DAY
    )
    used = profile.get("questions_used_today", 0) or 0

    return used < limit, used, limit


def increment_question_count(user_id: str) -> None:
    """
    Increment question count for today.
    Always fetches fresh from DB — never uses cache.
    """
    profile = get_profile(user_id)
    if not profile:
        return
    profile = _reset_usage_if_needed(profile)
    used    = profile.get("questions_used_today", 0) or 0
    update_profile(user_id, {"questions_used_today": used + 1})
    _invalidate_profile_cache()


# ─────────────────────────────────────────────────────────────────────────────
# Simulation run operations
# ─────────────────────────────────────────────────────────────────────────────

def save_simulation_run(
    user_id: str,
    prompt: str,
    params: dict,
    metrics: dict,
    insights: list[str],
    telemetry: list[dict],
    duration_sec: float = 0.0,
) -> str:
    """
    Save a simulation run to Supabase.
    Returns the new run UUID.
    """
    client = get_client()

    clean_telemetry = []
    for row in telemetry:
        clean_row = dict(row)
        clean_row["is_charging"] = bool(clean_row.get("is_charging", False))
        clean_telemetry.append(clean_row)

    data = {
        "user_id":      user_id,
        "prompt":       prompt,
        "params":       params,
        "metrics":      metrics,
        "insights":     insights,
        "telemetry":    clean_telemetry,
        "duration_sec": duration_sec,
    }

    response = client.table("simulation_runs_v2").insert(data).execute()
    return response.data[0]["id"] if response.data else ""


def get_all_simulation_runs(user_id: str, limit: int = 50) -> list[dict]:
    """Fetch all simulation runs for a user (no telemetry — summary only)."""
    client = get_client()
    response = (
        client.table("simulation_runs_v2")
        .select("id, created_at, prompt, metrics")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data or []


def get_simulation_run_by_id(run_id: str, user_id: str) -> Optional[dict]:
    """Fetch a single simulation run by ID (with telemetry)."""
    client = get_client()
    response = (
        client.table("simulation_runs_v2")
        .select("*")
        .eq("id", run_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not response.data:
        return None

    run = response.data[0]

    telemetry = run.get("telemetry", [])
    for row in telemetry:
        row["is_charging"] = bool(row.get("is_charging", False))
    run["telemetry"] = telemetry

    return run


def get_runs_for_comparison(
    run_ids: list[str],
    user_id: str,
) -> list[dict]:
    """Fetch multiple runs for comparison — all must belong to user."""
    return [
        r for rid in run_ids
        if (r := get_simulation_run_by_id(rid, user_id)) is not None
    ]


def delete_simulation_run(run_id: str, user_id: str) -> None:
    """Delete a simulation run (only if it belongs to the user)."""
    client = get_client()
    client.table("simulation_runs_v2") \
        .delete() \
        .eq("id", run_id) \
        .eq("user_id", user_id) \
        .execute()


# ─────────────────────────────────────────────────────────────────────────────
# Chat history operations
# ─────────────────────────────────────────────────────────────────────────────

def save_chat_message(
    user_id: str,
    question: str,
    answer: str,
    sources: list[str],
    simulation_context: Optional[dict] = None,
) -> None:
    """Save a Q&A pair to chat history."""
    client = get_client()
    data = {
        "user_id":            user_id,
        "question":           question,
        "answer":             answer,
        "sources":            sources,
        "simulation_context": simulation_context or {},
    }
    client.table("chat_history").insert(data).execute()


def get_chat_history(user_id: str, limit: int = 20) -> list[dict]:
    """Fetch recent chat history for a user."""
    client = get_client()
    response = (
        client.table("chat_history")
        .select("question, answer, sources, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return list(reversed(response.data or []))


def clear_chat_history(user_id: str) -> None:
    """Delete all chat history for a user."""
    client = get_client()
    client.table("chat_history") \
        .delete() \
        .eq("user_id", user_id) \
        .execute()


# ─────────────────────────────────────────────────────────────────────────────
# Feedback operations
# ─────────────────────────────────────────────────────────────────────────────

def save_feedback(
    user_id: str,
    feedback_type: str,
    message: str,
    severity: str = "low",
) -> None:
    """Save user feedback or bug report."""
    client = get_client()
    data = {
        "user_id":       user_id,
        "feedback_type": feedback_type,
        "message":       message,
        "severity":      severity,
        "status":        "open",
    }
    client.table("feedback").insert(data).execute()