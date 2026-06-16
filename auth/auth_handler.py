"""
auth/auth_handler.py

Supabase authentication logic for GenEV 2.0.

Functions
---------
- sign_up()        — create new account + profile
- sign_in()        — login with email/password
- sign_out()       — logout current session
- is_logged_in()   — check if user is authenticated
- get_user_id()    — get current user's UUID
- get_user_email() — get current user's email
"""

import streamlit as st
from typing import Optional

from database.supabase_client import (
    get_client,
    get_service_client,
    set_auth_token,
    create_profile,
    get_profile,
)


# ─────────────────────────────────────────────────────────────────────────────
# Session state keys
# ─────────────────────────────────────────────────────────────────────────────

_SESSION_KEY = "genev_session"
_USER_KEY    = "genev_user"
_PROFILE_KEY = "genev_profile"
_TOKEN_KEY   = "genev_access_token"

_LS_ACCESS_KEY  = "genev_access_token"
_LS_REFRESH_KEY = "genev_refresh_token"


# ─────────────────────────────────────────────────────────────────────────────
# localStorage persistence
# ─────────────────────────────────────────────────────────────────────────────

def _save_to_storage(access_token: str, refresh_token: str) -> None:
    """Save tokens to browser localStorage."""
    try:
        from streamlit_js_eval import streamlit_js_eval
        streamlit_js_eval(
            js_expressions=f"localStorage.setItem('{_LS_ACCESS_KEY}', '{access_token}'); "
                           f"localStorage.setItem('{_LS_REFRESH_KEY}', '{refresh_token}');",
            key="save_tokens",
        )
    except Exception as e:
        print(f"[auth] localStorage save failed: {e}")


def _clear_storage() -> None:
    """Clear auth tokens from browser localStorage."""
    try:
        from streamlit_js_eval import streamlit_js_eval
        streamlit_js_eval(
            js_expressions=f"localStorage.removeItem('{_LS_ACCESS_KEY}'); "
                           f"localStorage.removeItem('{_LS_REFRESH_KEY}');",
            key="clear_tokens",
        )
    except Exception as e:
        print(f"[auth] localStorage clear failed: {e}")


def _get_from_storage(key: str, state_key: str) -> Optional[str]:
    """Read a single value from browser localStorage."""
    try:
        from streamlit_js_eval import streamlit_js_eval
        val = streamlit_js_eval(
            js_expressions=f"localStorage.getItem('{key}')",
            key=state_key,
        )
        return val if val and val != "null" else None
    except Exception as e:
        print(f"[auth] localStorage read failed: {e}")
        return None


def _restore_from_storage() -> bool:
    """
    Try to restore session from browser localStorage.
    Uses refresh_token first, then access_token as fallback.
    """
    try:
        refresh_token = _get_from_storage(_LS_REFRESH_KEY, "read_refresh_token")
        access_token  = _get_from_storage(_LS_ACCESS_KEY,  "read_access_token")

        if not refresh_token and not access_token:
            return False

        client = get_client()

        # Try refresh token first — most reliable
        if refresh_token:
            try:
                response = client.auth.refresh_session(refresh_token)
                if response and response.session:
                    _store_session(response)
                    return True
            except Exception:
                pass

        # Fall back to access token
        if access_token:
            try:
                set_auth_token(access_token)
                response = client.auth.get_user(access_token)
                if response and response.user:
                    st.session_state[_USER_KEY]    = response.user
                    st.session_state[_TOKEN_KEY]   = access_token
                    profile = get_profile(response.user.id)
                    st.session_state[_PROFILE_KEY] = profile
                    return True
            except Exception:
                pass

    except Exception as e:
        print(f"[auth] Storage restore failed: {e}")

    return False


# ─────────────────────────────────────────────────────────────────────────────
# Sign up
# ─────────────────────────────────────────────────────────────────────────────

def sign_up(
    email: str,
    password: str,
    name: str,
    city: str = "",
    daily_commute_km: float = 30.0,
    has_home_charging: bool = False,
    driving_style: str = "moderate",
) -> tuple[bool, str]:
    """
    Create a new Supabase auth user and profile.
    Profile is created using service role client to bypass RLS.
    """
    client = get_client()

    try:
        response = client.auth.sign_up({
            "email":    email,
            "password": password,
        })

        if not response.user:
            return False, "Signup failed. Please try again."

        user_id = response.user.id

        try:
            create_profile(
                user_id=user_id,
                name=name,
                email=email,
                city=city,
                daily_commute_km=daily_commute_km,
                has_home_charging=has_home_charging,
                driving_style=driving_style,
            )
        except Exception as profile_error:
            print(f"[auth] Profile creation failed: {profile_error}")

        if response.session:
            _store_session(response)
            return True, "Account created successfully!"

        return True, "Account created! Please check your email."

    except Exception as e:
        error_msg = str(e)
        if "already registered" in error_msg.lower() or "user already registered" in error_msg.lower():
            return False, "An account with this email already exists. Please log in."
        if "password" in error_msg.lower():
            return False, "Password must be at least 6 characters."
        return False, f"Signup error: {error_msg}"


# ─────────────────────────────────────────────────────────────────────────────
# Sign in
# ─────────────────────────────────────────────────────────────────────────────

def sign_in(email: str, password: str) -> tuple[bool, str]:
    """Sign in with email and password."""
    client = get_client()

    try:
        response = client.auth.sign_in_with_password({
            "email":    email,
            "password": password,
        })

        if not response.user or not response.session:
            return False, "Invalid email or password."

        _store_session(response)

        # Safety net — create profile if missing
        user_id = response.user.id
        profile = get_profile(user_id)
        if not profile:
            try:
                create_profile(
                    user_id=user_id,
                    name=email.split("@")[0],
                    email=email,
                )
                st.session_state[_PROFILE_KEY] = get_profile(user_id)
            except Exception as e:
                print(f"[auth] Profile creation on login failed: {e}")

        return True, "Welcome back!"

    except Exception as e:
        error_msg = str(e)
        if "invalid" in error_msg.lower() or "credentials" in error_msg.lower():
            return False, "Invalid email or password."
        if "email" in error_msg.lower() and "confirm" in error_msg.lower():
            return (
                False,
                "Please verify your email first. "
                "Check your inbox for the verification link from GenEV.",
            )
        return False, f"Login error: {error_msg}"


# ─────────────────────────────────────────────────────────────────────────────
# Sign out
# ─────────────────────────────────────────────────────────────────────────────

def sign_out() -> None:
    """Sign out current user and clear session state + localStorage."""
    try:
        client = get_client()
        client.auth.sign_out()
    except Exception:
        pass

    _clear_storage()

    for key in [_SESSION_KEY, _USER_KEY, _PROFILE_KEY, _TOKEN_KEY]:
        if key in st.session_state:
            del st.session_state[key]

    for key in ["last_result", "last_metrics", "last_run_id",
                "preset_prompt", "prompt_input", "chat_messages",
                "show_auth"]:
        if key in st.session_state:
            del st.session_state[key]


# ─────────────────────────────────────────────────────────────────────────────
# Session helpers
# ─────────────────────────────────────────────────────────────────────────────

def _store_session(response) -> None:
    """Store auth session in Streamlit state and localStorage."""
    st.session_state[_SESSION_KEY] = response.session
    st.session_state[_USER_KEY]    = response.user
    st.session_state[_TOKEN_KEY]   = response.session.access_token

    set_auth_token(response.session.access_token)

    profile = get_profile(response.user.id)
    st.session_state[_PROFILE_KEY] = profile

    _save_to_storage(
        response.session.access_token,
        response.session.refresh_token,
    )


def restore_session() -> bool:
    """Attempt to restore session from state or localStorage."""
    # 1. Try existing session state token
    token = st.session_state.get(_TOKEN_KEY)
    if token:
        try:
            set_auth_token(token)
            client   = get_client()
            response = client.auth.get_user(token)
            if response and response.user:
                st.session_state[_USER_KEY]    = response.user
                profile = get_profile(response.user.id)
                st.session_state[_PROFILE_KEY] = profile
                return True
        except Exception:
            pass

    # 2. Try localStorage
    return _restore_from_storage()


def is_logged_in() -> bool:
    """Check if a user is currently logged in."""
    return (
        _USER_KEY  in st.session_state
        and st.session_state[_USER_KEY] is not None
        and _TOKEN_KEY in st.session_state
    )


def get_user_id() -> Optional[str]:
    """Get current user's UUID."""
    user = st.session_state.get(_USER_KEY)
    return user.id if user else None


def get_user_email() -> Optional[str]:
    """Get current user's email."""
    user = st.session_state.get(_USER_KEY)
    return user.email if user else None


def get_profile_cached() -> Optional[dict]:
    """Get profile from cache or fetch fresh."""
    profile = st.session_state.get(_PROFILE_KEY)
    if profile:
        return profile
    user_id = get_user_id()
    if not user_id:
        return None
    profile = get_profile(user_id)
    st.session_state[_PROFILE_KEY] = profile
    return profile


def refresh_profile() -> Optional[dict]:
    """Force refresh user profile from Supabase."""
    user_id = get_user_id()
    if not user_id:
        return None
    profile = get_profile(user_id)
    st.session_state[_PROFILE_KEY] = profile
    return profile


def get_user_name() -> str:
    """Get current user's display name."""
    profile = get_profile_cached()
    if profile and profile.get("name"):
        return profile["name"]
    email = get_user_email()
    return email.split("@")[0] if email else "User"


def get_subscription_plan() -> str:
    """Get current user's subscription plan — always fresh."""
    user_id = get_user_id()
    if not user_id:
        return "free"
    profile = get_profile(user_id)
    if profile:
        st.session_state[_PROFILE_KEY] = profile
        return profile.get("subscription_plan", "free")
    return "free"


def is_premium() -> bool:
    """Check if current user has premium plan."""
    return get_subscription_plan() == "premium"