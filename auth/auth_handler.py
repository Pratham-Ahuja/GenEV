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
    set_auth_token,
    create_profile,
    get_profile,
)


# ─────────────────────────────────────────────────────────────────────────────
# Session state keys
# ─────────────────────────────────────────────────────────────────────────────

_SESSION_KEY     = "genev_session"
_USER_KEY        = "genev_user"
_PROFILE_KEY     = "genev_profile"
_TOKEN_KEY       = "genev_access_token"
_COOKIE_PASSWORD = "genev_secret_cookie_key_2025"
_COOKIE_PREFIX   = "genev_"


# ─────────────────────────────────────────────────────────────────────────────
# Cookie manager
# ─────────────────────────────────────────────────────────────────────────────

def _get_cookies():
    """Get the encrypted cookie manager instance."""
    try:
        from streamlit_cookies_manager import EncryptedCookieManager
        cookies = EncryptedCookieManager(
            prefix=_COOKIE_PREFIX,
            password=_COOKIE_PASSWORD,
        )
        return cookies
    except ImportError:
        print("[auth] streamlit-cookies-manager not installed. "
              "Run: pip install streamlit-cookies-manager")
        return None
    except Exception as e:
        print(f"[auth] Cookie manager init failed: {e}")
        return None


def _save_to_cookie(access_token: str, refresh_token: str) -> None:
    """Save tokens to browser cookie for persistence."""
    try:
        cookies = _get_cookies()
        if cookies is None:
            return
        if not cookies.ready():
            return
        cookies["access_token"]  = access_token
        cookies["refresh_token"] = refresh_token
        cookies.save()
    except Exception as e:
        print(f"[auth] Cookie save failed: {e}")


def _clear_cookie() -> None:
    """Clear auth tokens from browser cookie."""
    try:
        cookies = _get_cookies()
        if cookies is None:
            return
        if not cookies.ready():
            return
        cookies["access_token"]  = ""
        cookies["refresh_token"] = ""
        cookies.save()
    except Exception as e:
        print(f"[auth] Cookie clear failed: {e}")


def _restore_from_cookie() -> bool:
    """
    Try to restore session from browser cookie.
    Uses refresh_token first (more reliable), then access_token.
    Returns True if session restored successfully.
    """
    try:
        cookies = _get_cookies()
        if cookies is None:
            return False
        if not cookies.ready():
            return False

        refresh_token = cookies.get("refresh_token", "")
        access_token  = cookies.get("access_token", "")

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
                    st.session_state[_USER_KEY]  = response.user
                    st.session_state[_TOKEN_KEY] = access_token
                    profile = get_profile(response.user.id)
                    st.session_state[_PROFILE_KEY] = profile
                    return True
            except Exception:
                pass

    except Exception as e:
        print(f"[auth] Cookie restore failed: {e}")

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

    Returns
    -------
    (success, message)
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

        create_profile(
            user_id=user_id,
            name=name,
            email=email,
            city=city,
            daily_commute_km=daily_commute_km,
            has_home_charging=has_home_charging,
            driving_style=driving_style,
        )

        if response.session:
            _store_session(response)
            return True, "Account created successfully!"

        return True, "Account created! Please log in."

    except Exception as e:
        error_msg = str(e)
        if "already registered" in error_msg.lower():
            return False, "This email is already registered. Please log in."
        if "password" in error_msg.lower():
            return False, "Password must be at least 6 characters."
        return False, f"Signup error: {error_msg}"


# ─────────────────────────────────────────────────────────────────────────────
# Sign in
# ─────────────────────────────────────────────────────────────────────────────

def sign_in(email: str, password: str) -> tuple[bool, str]:
    """
    Sign in with email and password.

    Returns
    -------
    (success, message)
    """
    client = get_client()

    try:
        response = client.auth.sign_in_with_password({
            "email":    email,
            "password": password,
        })

        if not response.user or not response.session:
            return False, "Invalid email or password."

        _store_session(response)
        return True, "Welcome back!"

    except Exception as e:
        error_msg = str(e)
        if "invalid" in error_msg.lower() or "credentials" in error_msg.lower():
            return False, "Invalid email or password."
        if "email" in error_msg.lower() and "confirm" in error_msg.lower():
            return False, "Please confirm your email before logging in."
        return False, f"Login error: {error_msg}"


# ─────────────────────────────────────────────────────────────────────────────
# Sign out
# ─────────────────────────────────────────────────────────────────────────────

def sign_out() -> None:
    """Sign out current user and clear session state + cookies."""
    try:
        client = get_client()
        client.auth.sign_out()
    except Exception:
        pass

    # Clear browser cookie
    _clear_cookie()

    # Clear session state
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
    """Store auth session in Streamlit state and browser cookie."""
    st.session_state[_SESSION_KEY] = response.session
    st.session_state[_USER_KEY]    = response.user
    st.session_state[_TOKEN_KEY]   = response.session.access_token

    set_auth_token(response.session.access_token)

    profile = get_profile(response.user.id)
    st.session_state[_PROFILE_KEY] = profile

    # Persist to cookie for refresh/reopen persistence
    _save_to_cookie(
        response.session.access_token,
        response.session.refresh_token,
    )


def restore_session() -> bool:
    """
    Attempt to restore session.
    Order: session state token → browser cookie.
    Returns True if session is valid.
    """
    # 1. Try existing session state token (same tab, no refresh)
    token = st.session_state.get(_TOKEN_KEY)
    if token:
        try:
            set_auth_token(token)
            client   = get_client()
            response = client.auth.get_user(token)
            if response and response.user:
                st.session_state[_USER_KEY] = response.user
                profile = get_profile(response.user.id)
                st.session_state[_PROFILE_KEY] = profile
                return True
        except Exception:
            pass

    # 2. Try browser cookie (after refresh or reopen)
    return _restore_from_cookie()


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
    """Get profile from cache or fetch fresh from Supabase."""
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