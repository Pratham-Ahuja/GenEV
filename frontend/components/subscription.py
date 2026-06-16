"""
frontend/components/subscription.py

Subscription and pricing UI for GenEV 2.0.

Sections
--------
1. render_subscription_page() — full pricing page
2. render_current_plan()      — current plan status card
3. render_usage_stats()       — daily usage breakdown
4. render_pricing_cards()     — free vs premium comparison
5. render_upgrade_section()   — premium code activation + contact
6. render_premium_active()    — premium active confirmation
7. render_faq()               — frequently asked questions
"""

import streamlit as st
from datetime import date

from auth.auth_handler import (
    get_user_id,
    get_user_name,
    get_profile_cached,
    refresh_profile,
    is_premium,
)
from database.supabase_client import (
    check_simulation_limit,
    check_question_limit,
    update_profile,
    generate_premium_code,
    get_premium_code_status,
    validate_and_activate_premium,
    check_and_expire_premium,
)
from config import (
    FREE_SIMULATIONS_PER_DAY,
    FREE_QUESTIONS_PER_DAY,
    PREMIUM_SIMULATIONS_PER_DAY,
    PREMIUM_QUESTIONS_PER_DAY,
    PREMIUM_PRICE_INR,
    FREE_FEATURES,
    PREMIUM_FEATURES,
)


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def render_subscription_page() -> None:
    """Full subscription and pricing page."""
    user_id = get_user_id()
    if not user_id:
        st.warning("Please log in to view subscription details.", icon="⚠️")
        return

    # Check and expire premium if billing period ended
    check_and_expire_premium(user_id)

    st.markdown("## 💎 Plans & Pricing")
    st.markdown(
        "<p style='color:#64748B;font-size:13px;margin-bottom:20px;'>"
        "Choose the plan that fits your EV intelligence needs.</p>",
        unsafe_allow_html=True,
    )

    render_current_plan()
    st.divider()
    render_usage_stats(user_id)
    st.divider()
    render_pricing_cards()
    st.divider()

    if not is_premium():
        render_upgrade_section(user_id)
    else:
        render_premium_active(user_id)

    st.divider()
    render_faq()


# ─────────────────────────────────────────────────────────────────────────────
# Current plan card
# ─────────────────────────────────────────────────────────────────────────────

def render_current_plan() -> None:
    """Render current plan status card."""
    profile = get_profile_cached()
    plan    = profile.get("subscription_plan", "free") if profile else "free"
    name    = get_user_name()

    if plan == "premium":
        bg       = "rgba(124,58,237,0.06)"
        border   = "rgba(124,58,237,0.25)"
        badge_bg = "#EDE9FE"
        badge_fg = "#7C3AED"
        icon     = "⭐"
        label    = "Premium"
        desc     = "You have full access to all GenEV features."
    else:
        bg       = "rgba(29,158,117,0.06)"
        border   = "rgba(29,158,117,0.25)"
        badge_bg = "#E1F5EE"
        badge_fg = "#1D9E75"
        icon     = "✅"
        label    = "Free"
        desc     = f"Upgrade to Premium for {PREMIUM_QUESTIONS_PER_DAY} AI questions/day and PDF exports."

    st.markdown(
        f'<div style="background:{bg};border:1px solid {border};'
        f'border-radius:14px;padding:20px 24px;margin-bottom:8px;">'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;margin-bottom:8px;">'
        f'<div style="font-size:16px;font-weight:700;color:#1E293B;">'
        f'👤 {name}</div>'
        f'<span style="background:{badge_bg};color:{badge_fg};'
        f'font-size:13px;font-weight:600;padding:4px 14px;'
        f'border-radius:20px;">{icon} {label} Plan</span>'
        f'</div>'
        f'<div style="font-size:13px;color:#475569;">{desc}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Usage stats
# ─────────────────────────────────────────────────────────────────────────────

def render_usage_stats(user_id: str) -> None:
    """Render today's usage breakdown."""
    st.markdown("### 📊 Today's Usage")

    sim_allowed, sim_used, sim_limit = check_simulation_limit(user_id)
    q_allowed,   q_used,   q_limit   = check_question_limit(user_id)

    col1, col2 = st.columns(2)
    with col1:
        _render_usage_bar(
            label="Simulations",
            used=sim_used,
            limit=sim_limit,
            icon="🧪",
            color="#1D9E75" if sim_allowed else "#DC2626",
        )
    with col2:
        _render_usage_bar(
            label="AI Questions",
            used=q_used,
            limit=q_limit,
            icon="🤖",
            color="#1D9E75" if q_allowed else "#DC2626",
        )

    st.markdown(
        f'<p style="font-size:11px;color:#94A3B8;margin-top:6px;">'
        f'🔄 Usage resets daily at midnight · Today: {date.today().strftime("%B %d, %Y")}'
        f'</p>',
        unsafe_allow_html=True,
    )


def _render_usage_bar(
    label: str,
    used: int,
    limit: int,
    icon: str,
    color: str,
) -> None:
    pct       = min(100, int((used / limit) * 100)) if limit > 0 else 100
    remaining = max(0, limit - used)

    if limit >= 999:
        bar_display = "∞ Unlimited"
        pct_display = 0
    else:
        bar_display = f"{used}/{limit}"
        pct_display = pct

    st.markdown(
        f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;'
        f'border-radius:12px;padding:14px 16px;">'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;margin-bottom:8px;">'
        f'<span style="font-size:13px;font-weight:600;color:#1E293B;">'
        f'{icon} {label}</span>'
        f'<span style="font-size:13px;font-weight:600;color:{color};">'
        f'{bar_display}</span>'
        f'</div>'
        f'<div style="background:#E2E8F0;border-radius:4px;height:8px;'
        f'margin-bottom:6px;">'
        f'<div style="background:{color};height:8px;border-radius:4px;'
        f'width:{pct_display}%;transition:width 0.3s;"></div>'
        f'</div>'
        f'<div style="font-size:11px;color:#64748B;">'
        f'{"Unlimited remaining" if limit >= 999 else f"{remaining} remaining today"}'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Pricing cards
# ─────────────────────────────────────────────────────────────────────────────

def render_pricing_cards() -> None:
    st.markdown("### 🏷️ Plans")
    col1, col2 = st.columns(2)

    with col1:
        _render_plan_card(
            name="GenEV Free",
            price="₹0",
            period="forever",
            features=FREE_FEATURES,
            is_current=not is_premium(),
            highlight=False,
            badge="Current Plan" if not is_premium() else "",
        )
    with col2:
        _render_plan_card(
            name="GenEV Premium",
            price=f"₹{PREMIUM_PRICE_INR}",
            period="per month",
            features=PREMIUM_FEATURES,
            is_current=is_premium(),
            highlight=True,
            badge="Most Popular" if not is_premium() else "Active",
        )


def _render_plan_card(
    name: str,
    price: str,
    period: str,
    features: list[str],
    is_current: bool,
    highlight: bool,
    badge: str = "",
) -> None:
    border  = "#7C3AED" if highlight else "#E2E8F0"
    bg      = "rgba(124,58,237,0.03)" if highlight else "#F8FAFC"
    heading = "#7C3AED" if highlight else "#1E293B"

    badge_html = ""
    if badge:
        badge_bg = "#EDE9FE" if highlight else "#E1F5EE"
        badge_fg = "#7C3AED" if highlight else "#1D9E75"
        badge_html = (
            f'<span style="background:{badge_bg};color:{badge_fg};'
            f'font-size:11px;font-weight:600;padding:2px 10px;'
            f'border-radius:20px;">{badge}</span>'
        )

    features_html = "".join([
        f'<div style="display:flex;align-items:flex-start;gap:8px;'
        f'margin-bottom:8px;">'
        f'<span style="color:#1D9E75;font-size:14px;flex-shrink:0;">✓</span>'
        f'<span style="font-size:13px;color:#1E293B;">{f}</span>'
        f'</div>'
        for f in features
    ])

    st.markdown(
        f'<div style="background:{bg};border:2px solid {border};'
        f'border-radius:16px;padding:24px;height:100%;">'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:flex-start;margin-bottom:12px;">'
        f'<div style="font-size:16px;font-weight:700;color:{heading};">'
        f'{name}</div>'
        f'{badge_html}'
        f'</div>'
        f'<div style="margin-bottom:16px;">'
        f'<span style="font-size:32px;font-weight:800;color:{heading};">'
        f'{price}</span>'
        f'<span style="font-size:13px;color:#64748B;margin-left:4px;">'
        f'/{period}</span>'
        f'</div>'
        f'<div style="margin-bottom:16px;">{features_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Upgrade section — premium code system
# ─────────────────────────────────────────────────────────────────────────────

def render_upgrade_section(user_id: str) -> None:
    """Render upgrade section with unique code generation and activation."""
    st.markdown("### 🚀 Upgrade to Premium")

    # ── Step 1: Show/generate user's unique code ──────────────────────────────
    st.markdown(
        '<div style="background:rgba(124,58,237,0.06);'
        'border:1px solid rgba(124,58,237,0.20);'
        'border-radius:14px;padding:20px 24px;margin-bottom:16px;">'
        '<div style="font-size:15px;font-weight:700;color:#1E293B;'
        'margin-bottom:10px;">Step 1 — Get your unique payment code</div>'
        '<div style="font-size:13px;color:#475569;line-height:1.7;">'
        'Your unique code below is linked to your account. '
        'Share it with us when making the payment so we can activate '
        'your Premium access.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Generate or fetch existing code
    with st.spinner("Loading your code..."):
        code_record = get_premium_code_status(user_id)
        if not code_record:
            user_code = generate_premium_code(user_id)
        else:
            user_code = code_record["code"]

    st.markdown(
        f'<div style="background:#F8FAFC;border:2px dashed #7C3AED;'
        f'border-radius:12px;padding:16px;text-align:center;'
        f'margin-bottom:16px;">'
        f'<div style="font-size:11px;color:#64748B;margin-bottom:6px;">'
        f'YOUR UNIQUE PREMIUM CODE</div>'
        f'<div style="font-size:24px;font-weight:800;color:#7C3AED;'
        f'letter-spacing:0.1em;">{user_code}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Step 2: Payment instructions ─────────────────────────────────────────
    st.markdown(
        f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;'
        f'border-radius:14px;padding:20px 24px;margin-bottom:16px;">'
        f'<div style="font-size:15px;font-weight:700;color:#1E293B;'
        f'margin-bottom:12px;">Step 2 — Make payment</div>'
        f'<div style="font-size:13px;color:#475569;line-height:2;">'
        f'💰 Amount: <strong>₹{PREMIUM_PRICE_INR}/month</strong><br>'
        f'📧 Send payment to: <strong>prathamahuja924@gmail.com</strong><br>'
        f'📝 Email subject: <strong>GenEV Premium — {user_code}</strong><br>'
        f'🧾 Include: Your name, transaction ID, and the code above'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Step 3: Activate with code ────────────────────────────────────────────
    st.markdown(
        '<div style="background:#F8FAFC;border:1px solid #E2E8F0;'
        'border-radius:14px;padding:20px 24px;margin-bottom:16px;">'
        '<div style="font-size:15px;font-weight:700;color:#1E293B;'
        'margin-bottom:10px;">Step 3 — Activate after payment confirmation</div>'
        '<div style="font-size:13px;color:#475569;margin-bottom:12px;">'
        'Once we confirm your payment (usually within a few hours), '
        'enter your code below to activate Premium.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        entered_code = st.text_input(
            "Enter your premium code",
            placeholder=f"e.g. {user_code}",
            key="premium_code_input",
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⭐ Activate Premium", key="activate_premium_btn",
                     use_container_width=True):
            if not entered_code.strip():
                st.error("Please enter your premium code.", icon="⚠️")
            else:
                with st.spinner("Verifying code..."):
                    success, message = validate_and_activate_premium(
                        user_id, entered_code.strip()
                    )
                if success:
                    st.success(message, icon="✅")
                    st.balloons()
                    refresh_profile()
                    st.rerun()
                else:
                    st.error(message, icon="🔴")

    st.markdown(
        '<p style="font-size:11px;color:#94A3B8;margin-top:8px;">'
        '🔒 Your code is unique to your account and cannot be used by anyone else.'
        '</p>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Premium active section
# ─────────────────────────────────────────────────────────────────────────────

def render_premium_active(user_id: str) -> None:
    """Show premium active status with billing info."""
    code_record = get_premium_code_status(user_id)
    billing_end = code_record.get("billing_period_end") if code_record else None

    billing_str = ""
    if billing_end:
        billing_str = (
            f'<br><div style="font-size:12px;color:#7C3AED;margin-top:6px;">'
            f'📅 Valid until: <strong>{billing_end}</strong></div>'
        )

    st.markdown(
        f'<div style="background:rgba(124,58,237,0.06);'
        f'border:1px solid rgba(124,58,237,0.25);'
        f'border-radius:14px;padding:20px 24px;text-align:center;">'
        f'<div style="font-size:28px;margin-bottom:8px;">⭐</div>'
        f'<div style="font-size:17px;font-weight:700;color:#7C3AED;'
        f'margin-bottom:6px;">Premium Active</div>'
        f'<div style="font-size:13px;color:#475569;">'
        f'You have full access to all GenEV features including '
        f'unlimited AI questions and PDF exports.'
        f'{billing_str}'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    with st.expander("⚙️ Manage Subscription"):
        st.markdown(
            "To renew or cancel your subscription, contact us at "
            "**prathamahuja924@gmail.com** with subject "
            "'GenEV Subscription'."
        )
        if code_record:
            st.markdown(
                f"Your premium code: **{code_record.get('code', 'N/A')}**"
            )


# ─────────────────────────────────────────────────────────────────────────────
# FAQ
# ─────────────────────────────────────────────────────────────────────────────

def render_faq() -> None:
    st.markdown("### ❓ Frequently Asked Questions")

    faqs = [
        (
            "How does the Premium activation work?",
            "You get a unique code linked to your account. Make payment and "
            "email us with your code and transaction ID. Once we confirm payment, "
            "we mark it as received and you activate Premium by entering your code.",
        ),
        (
            "What happens when my billing period ends?",
            "Your Premium access is automatically disabled at the end of the "
            "billing period. To renew, make another payment and email us. "
            "We'll update your billing period and you can re-activate with the same code.",
        ),
        (
            "What happens when I reach my daily limit?",
            "Free users can run 3 simulations and ask 1 AI question per day. "
            "Limits reset at midnight. Premium users get unlimited simulations "
            f"and {PREMIUM_QUESTIONS_PER_DAY} AI questions per day.",
        ),
        (
            "Is my simulation data private?",
            "Yes. Row Level Security (RLS) ensures each user only sees "
            "their own simulations, chat history, and profile data.",
        ),
        (
            "Can I cancel Premium anytime?",
            "Yes. Contact prathamahuja924@gmail.com to cancel. "
            "You retain Premium access until the end of your billing period.",
        ),
        (
            "Is GenEV free to use?",
            f"Yes! The Free plan gives you {FREE_SIMULATIONS_PER_DAY} simulations/day, "
            f"{FREE_QUESTIONS_PER_DAY} AI question/day, full metrics dashboard, "
            "scenario comparison, and history — forever free.",
        ),
    ]

    for question, answer in faqs:
        with st.expander(question):
            st.markdown(
                f'<p style="font-size:13px;color:#1E293B;line-height:1.7;">'
                f'{answer}</p>',
                unsafe_allow_html=True,
            )