"""
frontend/components/subscription.py

Subscription and pricing UI for GenEV 2.0.

Sections
--------
1. render_subscription_page() — full pricing page
2. render_current_plan()      — current plan status card
3. render_usage_stats()       — daily usage breakdown
4. render_pricing_cards()     — free vs premium comparison
5. render_upgrade_modal()     — upgrade CTA with Razorpay-ready button
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

    st.markdown("## 💎 Plans & Pricing")
    st.markdown(
        "<p style='color:#64748B;font-size:13px;margin-bottom:20px;'>"
        "Choose the plan that fits your EV intelligence needs.</p>",
        unsafe_allow_html=True,
    )

    # Current plan + usage
    render_current_plan()
    st.divider()
    render_usage_stats(user_id)
    st.divider()

    # Pricing cards
    render_pricing_cards()
    st.divider()

    # Upgrade section
    if not is_premium():
        render_upgrade_section()
    else:
        render_premium_active()

    st.divider()

    # FAQ
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

    sim_allowed, sim_used, sim_limit   = check_simulation_limit(user_id)
    q_allowed,   q_used,   q_limit     = check_question_limit(user_id)

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

    # Reset info
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
    """Render a single usage progress bar."""
    pct   = min(100, int((used / limit) * 100)) if limit > 0 else 100
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
    """Render side-by-side free vs premium pricing cards."""
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
    """Render a single plan card."""
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
# Upgrade section
# ─────────────────────────────────────────────────────────────────────────────

def render_upgrade_section() -> None:
    """Render upgrade CTA section."""
    st.markdown("### 🚀 Upgrade to Premium")

    st.markdown(
        f'<div style="background:linear-gradient(135deg,'
        f'rgba(124,58,237,0.08),rgba(29,158,117,0.08));'
        f'border:1px solid rgba(124,58,237,0.20);'
        f'border-radius:16px;padding:24px;margin-bottom:16px;">'
        f'<div style="font-size:18px;font-weight:700;color:#1E293B;'
        f'margin-bottom:8px;">Unlock GenEV AI Intelligence</div>'
        f'<div style="font-size:13px;color:#475569;line-height:1.7;'
        f'margin-bottom:16px;">'
        f'Get {PREMIUM_QUESTIONS_PER_DAY} AI-powered EV questions per day, '
        f'unlimited simulations, PDF report exports, and priority '
        f'AI responses — all for just '
        f'<strong>₹{PREMIUM_PRICE_INR}/month</strong>.'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            f"⭐ Upgrade to Premium — ₹{PREMIUM_PRICE_INR}/month",
            use_container_width=True,
            key="upgrade_btn",
        ):
            _handle_upgrade()

    st.markdown(
        '<p style="text-align:center;font-size:11px;color:#94A3B8;'
        'margin-top:8px;">🔒 Secure payment · Cancel anytime · '
        'Instant activation</p>',
        unsafe_allow_html=True,
    )


def _handle_upgrade() -> None:
    """
    Handle upgrade button click.
    Currently shows demo activation — Razorpay integration ready.
    """
    st.markdown("---")
    st.markdown("### 💳 Complete Your Upgrade")

    st.info(
        "**Payment Gateway Coming Soon**\n\n"
        "Razorpay integration is being set up. "
        "For early access, contact us at "
        "prathamahuja924@gmail.com with subject "
        "'GenEV Premium Access'.",
        icon="ℹ️",
    )

    # Demo activation for testing
    st.markdown("**Demo Mode — Activate Premium for Testing:**")

    col1, col2 = st.columns(2)
    with col1:
        demo_code = st.text_input(
            "Enter demo code",
            placeholder="GENEV_PREMIUM_DEMO",
            key="demo_code_input",
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Activate Demo", key="activate_demo"):
            if demo_code.strip().upper() == "GENEV_PREMIUM_DEMO":
                _activate_premium_demo()
            else:
                st.error("Invalid demo code.", icon="🔴")


def _activate_premium_demo() -> None:
    """Activate premium for demo/testing purposes."""
    user_id = get_user_id()
    if not user_id:
        return

    try:
        update_profile(user_id, {"subscription_plan": "premium"})
        refresh_profile()
        st.success(
            "🎉 Premium activated! Enjoy all GenEV features.",
            icon="✅",
        )
        st.balloons()
        st.rerun()
    except Exception as e:
        st.error(f"Activation failed: {e}", icon="🔴")


# ─────────────────────────────────────────────────────────────────────────────
# Premium active section
# ─────────────────────────────────────────────────────────────────────────────

def render_premium_active() -> None:
    """Show premium active confirmation."""
    st.markdown(
        '<div style="background:rgba(124,58,237,0.06);'
        'border:1px solid rgba(124,58,237,0.25);'
        'border-radius:14px;padding:20px 24px;text-align:center;">'
        '<div style="font-size:28px;margin-bottom:8px;">⭐</div>'
        '<div style="font-size:17px;font-weight:700;color:#7C3AED;'
        'margin-bottom:6px;">Premium Active</div>'
        '<div style="font-size:13px;color:#475569;">'
        'You have full access to all GenEV features including '
        'unlimited AI questions and PDF exports.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # Manage subscription
    with st.expander("⚙️ Manage Subscription"):
        st.markdown(
            "To cancel or modify your subscription, contact us at "
            "**prathamahuja924@gmail.com** with subject "
            "'GenEV Subscription'."
        )
        if st.button(
            "Downgrade to Free",
            key="downgrade_btn",
        ):
            user_id = get_user_id()
            if user_id:
                update_profile(user_id, {"subscription_plan": "free"})
                refresh_profile()
                st.success("Downgraded to Free plan.", icon="✅")
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# FAQ
# ─────────────────────────────────────────────────────────────────────────────

def render_faq() -> None:
    """Render frequently asked questions."""
    st.markdown("### ❓ Frequently Asked Questions")

    faqs = [
        (
            "What happens when I reach my daily limit?",
            "Free users can run 3 simulations and ask 1 AI question per day. "
            "Limits reset at midnight. Premium users get unlimited simulations "
            f"and {PREMIUM_QUESTIONS_PER_DAY} AI questions per day.",
        ),
        (
            "Is the Premium plan worth it?",
            "If you use GenEV for serious EV research, buying decisions, "
            "or academic work — Premium gives you deeper AI analysis through "
            "10 questions/day, PDF reports you can save and share, "
            "and unlimited simulation runs.",
        ),
        (
            "Can I cancel Premium anytime?",
            "Yes. Contact prathamahuja924@gmail.com to cancel. "
            "You retain Premium access until the end of your billing period.",
        ),
        (
            "Is my simulation data private?",
            "Yes. Row Level Security (RLS) ensures each user only sees "
            "their own simulations, chat history, and profile data. "
            "No other user can access your data.",
        ),
        (
            "What payment methods are supported?",
            "Razorpay integration (UPI, cards, net banking) is coming soon. "
            "For early premium access, contact us directly.",
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