"""
auth/auth_ui.py

Complete authentication UI for GenEV 2.0.

Sections
--------
1. render_auth_page()           — main entry point (login or signup)
2. render_login_form()          — email/password login
3. render_signup_form()         — new account creation with profile setup
4. render_reset_password_page() — set new password after clicking reset link
5. render_profile_editor()      — edit profile settings
6. render_user_sidebar()        — sidebar user info + logout
"""

import time
import streamlit as st
from auth.auth_handler import (
    sign_in,
    sign_up,
    sign_out,
    get_user_name,
    get_user_email,
    get_profile_cached,
    refresh_profile,
    is_premium,
    get_user_id,
)
from database.supabase_client import update_profile, get_profile


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def render_auth_page() -> None:
    """
    Render the full authentication page.
    Shows login or signup form based on user selection.
    Called from app.py when user is not logged in.
    """

    # ── Back button to landing page ───────────────────────────────────────────
    col_back, col_space = st.columns([1, 5])
    with col_back:
        if st.button("← Back", key="auth_back_btn", use_container_width=True):
            st.session_state["show_auth"] = False
            st.rerun()

    # ── Hero section ──────────────────────────────────────────────────────────
    st.markdown(
        '<div style="text-align:center;padding:24px 20px 16px;">'
        '<div style="font-size:56px;margin-bottom:8px;">⚡</div>'
        '<div style="font-size:36px;font-weight:800;color:#1D9E75;'
        'letter-spacing:0.02em;margin-bottom:8px;">GenEV</div>'
        '<div style="font-size:16px;color:#475569;margin-bottom:4px;">'
        'AI-Powered EV Ownership Intelligence Platform'
        '</div>'
        '<div style="font-size:13px;color:#94A3B8;">'
        'Simulate · Analyse · Ask AI · Own Smarter'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Feature highlights ────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    features = [
        ("🧪", "EV Simulation",  "Realistic scenario generation"),
        ("🤖", "AI Chat",        "Ask questions about your EV"),
        ("📊", "Smart Metrics",  "6 performance metrics"),
        ("📄", "PDF Reports",    "Export your analysis"),
    ]
    for col, (icon, title, desc) in zip([col1, col2, col3, col4], features):
        with col:
            st.markdown(
                f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;'
                f'border-radius:12px;padding:16px;text-align:center;'
                f'margin-bottom:20px;">'
                f'<div style="font-size:24px;margin-bottom:6px;">{icon}</div>'
                f'<div style="font-size:13px;font-weight:600;color:#1E293B;'
                f'margin-bottom:4px;">{title}</div>'
                f'<div style="font-size:11px;color:#64748B;">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Auth tabs ─────────────────────────────────────────────────────────────
    tab_login, tab_signup, tab_forgot = st.tabs([
        "🔑 Login",
        "✨ Create Account",
        "🔓 Forgot Password",
    ])

    with tab_login:
        render_login_form()

    with tab_signup:
        render_signup_form()

    with tab_forgot:
        render_forgot_password_form()

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown(
        '<div style="text-align:center;padding:20px;color:#94A3B8;font-size:11px;">'
        'Built by <strong style="color:#1D9E75;">Pratham Ahuja</strong> · '
        'GenEV v2.0 · AI-Powered EV Intelligence'
        '</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Password reset page — shown when user clicks reset link from email
# ─────────────────────────────────────────────────────────────────────────────

def render_reset_password_page(access_token: str) -> None:
    """
    Render the set new password form.
    Called from app.py when URL contains access_token + type=recovery.
    After success, redirects to login page.
    """
    st.markdown(
        '<div style="text-align:center;padding:24px 20px 16px;">'
        '<div style="font-size:56px;margin-bottom:8px;">⚡</div>'
        '<div style="font-size:36px;font-weight:800;color:#1D9E75;'
        'margin-bottom:8px;">GenEV</div>'
        '<div style="font-size:13px;color:#94A3B8;">Reset Your Password</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown("### 🔐 Set New Password")
    st.markdown(
        "<p style='color:#64748B;font-size:13px;margin-bottom:20px;'>"
        "Enter your new password below.</p>",
        unsafe_allow_html=True,
    )

    with st.form("reset_password_form"):
        new_password = st.text_input(
            "New Password",
            type="password",
            placeholder="Min 6 characters",
            key="reset_new_password",
        )
        confirm_password = st.text_input(
            "Confirm New Password",
            type="password",
            placeholder="Repeat new password",
            key="reset_confirm_password",
        )

        col_btn, col_space = st.columns([1, 2])
        with col_btn:
            submitted = st.form_submit_button(
                "Update Password →",
                use_container_width=True,
            )

    if submitted:
        if not new_password or not confirm_password:
            st.error("Please fill in both fields.", icon="⚠️")
            return

        if new_password != confirm_password:
            st.error("Passwords do not match.", icon="⚠️")
            return

        if len(new_password) < 6:
            st.error("Password must be at least 6 characters.", icon="⚠️")
            return

        with st.spinner("Updating password..."):
            success, message = _update_password(access_token, new_password)

        if success:
            st.success(
                "✅ Password updated successfully! Redirecting to login...",
                icon="✅",
            )

            # Clear recovery token from session state
            if "recovery_token" in st.session_state:
                del st.session_state["recovery_token"]

            # Set show_auth so app.py routes to login page
            st.session_state["show_auth"] = True

            time.sleep(2)
            st.rerun()
        else:
            st.error(message, icon="🔴")


def _update_password(access_token: str, new_password: str) -> tuple[bool, str]:
    """Update user password using the recovery access token."""
    try:
        from database.supabase_client import get_client, set_auth_token
        client = get_client()

        # Set the recovery token so Supabase knows which user
        set_auth_token(access_token)

        # Update the password
        client.auth.update_user({"password": new_password})

        return True, "Password updated successfully!"

    except Exception as e:
        return False, f"Could not update password: {str(e)}"


# ─────────────────────────────────────────────────────────────────────────────
# Login form
# ─────────────────────────────────────────────────────────────────────────────

def render_login_form() -> None:
    """Render email/password login form."""
    st.markdown("### Welcome back")
    st.markdown(
        "<p style='color:#64748B;font-size:13px;margin-bottom:20px;'>"
        "Sign in to your GenEV workspace</p>",
        unsafe_allow_html=True,
    )

    with st.form("login_form", clear_on_submit=False):
        email = st.text_input(
            "Email address",
            placeholder="you@example.com",
            key="login_email",
        )
        password = st.text_input(
            "Password",
            type="password",
            placeholder="Your password",
            key="login_password",
        )

        col_btn, col_space = st.columns([1, 2])
        with col_btn:
            submitted = st.form_submit_button(
                "Sign In →",
                use_container_width=True,
            )

    if submitted:
        if not email or not password:
            st.error("Please enter both email and password.", icon="⚠️")
            return

        with st.spinner("Signing in..."):
            success, message = sign_in(email.strip(), password)

        if success:
            st.success(message, icon="✅")
            st.rerun()
        else:
            st.error(message, icon="🔴")

    st.markdown(
        '<p style="font-size:12px;color:#94A3B8;margin-top:8px;">'
        'Forgot your password? Use the <strong>Forgot Password</strong> tab above.</p>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Signup form
# ─────────────────────────────────────────────────────────────────────────────

def render_signup_form() -> None:
    """Render new account creation form with profile setup."""
    st.markdown("### Create your account")
    st.markdown(
        "<p style='color:#64748B;font-size:13px;margin-bottom:20px;'>"
        "Set up your personalized EV workspace</p>",
        unsafe_allow_html=True,
    )

    with st.form("signup_form", clear_on_submit=False):

        st.markdown("**Account Details**")
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input(
                "Full Name",
                placeholder="Pratham Ahuja",
                key="signup_name",
            )
        with col2:
            email = st.text_input(
                "Email Address",
                placeholder="you@example.com",
                key="signup_email",
            )

        col3, col4 = st.columns(2)
        with col3:
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Min 6 characters",
                key="signup_password",
            )
        with col4:
            confirm_password = st.text_input(
                "Confirm Password",
                type="password",
                placeholder="Repeat password",
                key="signup_confirm",
            )

        st.divider()

        st.markdown("**Your EV Profile**")
        st.markdown(
            "<p style='color:#64748B;font-size:12px;margin-bottom:12px;'>"
            "This helps GenEV personalise AI recommendations for you</p>",
            unsafe_allow_html=True,
        )

        col5, col6 = st.columns(2)
        with col5:
            city = st.text_input(
                "Your City",
                placeholder="Delhi, Mumbai, Bangalore...",
                key="signup_city",
            )
        with col6:
            commute = st.number_input(
                "Daily Commute (km)",
                min_value=0.0,
                max_value=500.0,
                value=30.0,
                step=5.0,
                key="signup_commute",
            )

        col7, col8 = st.columns(2)
        with col7:
            driving_style = st.selectbox(
                "Driving Style",
                options=["eco", "moderate", "aggressive"],
                index=1,
                key="signup_style",
            )
        with col8:
            home_charging = st.selectbox(
                "Home Charging Access",
                options=["Yes", "No"],
                key="signup_charging",
            )

        st.markdown("<br>", unsafe_allow_html=True)
        agree = st.checkbox(
            "I hereby declare that I have read and agree to all the terms "
            "and conditions as well as the privacy policy given on the "
            "Introduction page.",
            key="signup_agree",
        )

        submitted = st.form_submit_button(
            "Create Account →",
            use_container_width=True,
        )

    if submitted:
        if not all([name, email, password, confirm_password]):
            st.error("Please fill in all required fields.", icon="⚠️")
            return

        if not agree:
            st.error(
                "Please confirm that you have read and agree to the terms "
                "and conditions as well as the privacy policy to continue.",
                icon="⚠️",
            )
            return

        if password != confirm_password:
            st.error("Passwords do not match.", icon="⚠️")
            return

        if len(password) < 6:
            st.error("Password must be at least 6 characters.", icon="⚠️")
            return

        if "@" not in email:
            st.error("Please enter a valid email address.", icon="⚠️")
            return

        with st.spinner("Creating your account..."):
            success, message = sign_up(
                email=email.strip(),
                password=password,
                name=name.strip(),
                city=city.strip(),
                daily_commute_km=float(commute),
                has_home_charging=(home_charging == "Yes"),
                driving_style=driving_style,
            )

        if success:
            st.success(message, icon="✅")
            st.rerun()
        else:
            st.error(message, icon="🔴")


# ─────────────────────────────────────────────────────────────────────────────
# Forgot password form
# ─────────────────────────────────────────────────────────────────────────────

def render_forgot_password_form() -> None:
    """Render forgot password form."""
    st.markdown("### Reset your password")
    st.markdown(
        "<p style='color:#64748B;font-size:13px;margin-bottom:20px;'>"
        "Enter your registered email address and we'll send you a "
        "password reset link.</p>",
        unsafe_allow_html=True,
    )

    with st.form("forgot_password_form", clear_on_submit=True):
        email = st.text_input(
            "Registered Email Address",
            placeholder="you@example.com",
            key="forgot_email",
        )

        col_btn, col_space = st.columns([1, 2])
        with col_btn:
            submitted = st.form_submit_button(
                "Send Reset Link →",
                use_container_width=True,
            )

    if submitted:
        if not email or "@" not in email:
            st.error("Please enter a valid email address.", icon="⚠️")
            return

        with st.spinner("Sending reset link..."):
            success, message = _send_password_reset(email.strip())

        if success:
            st.success(message, icon="✅")
        else:
            st.error(message, icon="🔴")

    st.markdown(
        '<div style="background:#F8FAFC;border:1px solid #E2E8F0;'
        'border-radius:10px;padding:12px 16px;margin-top:16px;">'
        '<div style="font-size:12px;color:#475569;line-height:1.7;">'
        '<strong>ℹ️ How it works:</strong><br>'
        '1. Enter your registered email address above<br>'
        '2. Check your inbox for a password reset email from GenEV<br>'
        '3. Click the link in the email to set a new password<br>'
        '4. Return here and log in with your new password'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _send_password_reset(email: str) -> tuple[bool, str]:
    """Send a password reset email via Supabase Auth."""
    try:
        from database.supabase_client import get_client
        client = get_client()
        client.auth.reset_password_email(email)
        return (
            True,
            f"Password reset link sent to {email}. "
            "Please check your inbox (and spam folder)."
        )
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower() or "user" in error_msg.lower():
            return (
                True,
                f"If {email} is registered with GenEV, "
                "a reset link has been sent. Please check your inbox."
            )
        return False, f"Could not send reset email: {error_msg}"


# ─────────────────────────────────────────────────────────────────────────────
# Profile editor
# ─────────────────────────────────────────────────────────────────────────────

def render_profile_editor() -> None:
    """Render profile settings editor."""
    user_id = get_user_id()
    profile = get_profile_cached()

    if not profile:
        st.error("Could not load profile.", icon="🔴")
        return

    st.markdown("### ⚙️ Your Profile")
    st.markdown(
        "<p style='color:#64748B;font-size:13px;margin-bottom:20px;'>"
        "Update your EV profile to get better AI recommendations</p>",
        unsafe_allow_html=True,
    )

    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input(
                "Full Name",
                value=profile.get("name", ""),
            )
        with col2:
            city = st.text_input(
                "City",
                value=profile.get("city", ""),
            )

        col3, col4 = st.columns(2)
        with col3:
            commute = st.number_input(
                "Daily Commute (km)",
                min_value=0.0,
                max_value=500.0,
                value=float(profile.get("daily_commute_km", 30)),
                step=5.0,
            )
        with col4:
            style_options = ["eco", "moderate", "aggressive"]
            current_style = profile.get("driving_style", "moderate")
            style_idx     = (
                style_options.index(current_style)
                if current_style in style_options else 1
            )
            driving_style = st.selectbox(
                "Driving Style",
                options=style_options,
                index=style_idx,
            )

        home_charging = st.selectbox(
            "Home Charging Access",
            options=["Yes", "No"],
            index=0 if profile.get("has_home_charging") else 1,
        )

        saved = st.form_submit_button("Save Profile", use_container_width=True)

    if saved:
        updates = {
            "name":              name.strip(),
            "city":              city.strip(),
            "daily_commute_km":  float(commute),
            "driving_style":     driving_style,
            "has_home_charging": (home_charging == "Yes"),
        }
        with st.spinner("Saving..."):
            update_profile(user_id, updates)
            refresh_profile()
        st.success("Profile updated!", icon="✅")


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar user info
# ─────────────────────────────────────────────────────────────────────────────

def render_user_sidebar() -> None:
    """Render user info and logout button in sidebar."""
    profile = get_profile_cached()
    name    = get_user_name()
    email   = get_user_email()
    plan    = profile.get("subscription_plan", "free") if profile else "free"

    plan_color = "#1D9E75" if plan == "free" else "#7C3AED"
    plan_bg    = "#E1F5EE" if plan == "free" else "#EDE9FE"
    plan_label = "Free"    if plan == "free" else "Premium ⭐"

    st.markdown(
        f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;'
        f'border-radius:12px;padding:14px 16px;margin-bottom:12px;">'
        f'<div style="font-size:13px;font-weight:600;color:#1E293B;'
        f'margin-bottom:2px;">👤 {name}</div>'
        f'<div style="font-size:11px;color:#64748B;margin-bottom:8px;">'
        f'{email}</div>'
        f'<span style="background:{plan_bg};color:{plan_color};'
        f'font-size:11px;font-weight:600;padding:2px 10px;'
        f'border-radius:20px;">{plan_label}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if profile:
        sims_used  = profile.get("simulations_used_today", 0) or 0
        qs_used    = profile.get("questions_used_today", 0)   or 0
        sims_limit = 999 if plan == "premium" else 3
        qs_limit   = 10  if plan == "premium" else 1

        sims_color = "#DC2626" if sims_used >= sims_limit else "#1E293B"
        qs_color   = "#DC2626" if qs_used   >= qs_limit   else "#1E293B"

        st.markdown(
            f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;'
            f'border-radius:12px;padding:12px 16px;margin-bottom:12px;">'
            f'<div style="font-size:11px;color:#64748B;margin-bottom:8px;">'
            f'📊 Today\'s Usage</div>'
            f'<div style="font-size:12px;color:{sims_color};margin-bottom:4px;">'
            f'Simulations: <strong>{sims_used}/{sims_limit}</strong></div>'
            f'<div style="font-size:12px;color:{qs_color};">'
            f'AI Questions: <strong>{qs_used}/{qs_limit}</strong></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if st.button("🚪 Sign Out", use_container_width=True, key="logout_btn"):
        sign_out()
        st.rerun()