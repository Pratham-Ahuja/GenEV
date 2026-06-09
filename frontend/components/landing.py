"""
frontend/components/landing.py

Public landing page for GenEV — shown before login.
Gives visitors a compelling overview of the platform
before they sign up or log in.
"""

import streamlit as st
from config import APP_VERSION


def render_landing_page() -> bool:
    """
    Render the GenEV landing page.

    Returns
    -------
    bool — True if user clicked Login/Signup (trigger auth page)
    """

    # ── Hero Section ──────────────────────────────────────────────────────────
    st.markdown(
        '<div style="text-align:center;padding:48px 20px 24px;">'
        '<div style="font-size:64px;margin-bottom:8px;">⚡</div>'
        '<div style="font-size:42px;font-weight:900;color:#1D9E75;'
        'letter-spacing:0.02em;margin-bottom:8px;">GenEV</div>'
        '<div style="font-size:18px;font-weight:600;color:#1E293B;'
        'margin-bottom:10px;">'
        'AI-Powered EV Ownership Intelligence Platform'
        '</div>'
        '<div style="font-size:15px;color:#475569;max-width:580px;'
        'margin:0 auto;line-height:1.8;">'
        'Simulate real-world EV scenarios, analyse battery performance, '
        'ask AI-powered questions, and make smarter EV decisions — '
        'all built for <strong>Indian roads and conditions</strong>.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── CTA Buttons ───────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        get_started = st.button(
            "🚀 Get Started — Free",
            use_container_width=True,
            key="landing_get_started",
        )

    col4, col5, col6 = st.columns([2.2, 1.6, 2.2])
    with col5:
        st.markdown(
            '<p style="text-align:center;font-size:12px;color:#94A3B8;'
            'margin-top:-8px;">Already have an account? '
            '<span style="color:#1D9E75;font-weight:600;">Sign in below ↓</span></p>',
            unsafe_allow_html=True,
        )

    if get_started:
        st.session_state["show_auth"] = True
        st.rerun()

    st.divider()

    # ── What is GenEV ─────────────────────────────────────────────────────────
    st.markdown(
        '<div style="text-align:center;margin-bottom:20px;">'
        '<div style="font-size:22px;font-weight:700;color:#1E293B;">'
        'What is GenEV?</div>'
        '<div style="font-size:14px;color:#64748B;margin-top:6px;'
        'max-width:600px;margin:8px auto 0;">'
        'Most EV buyers make decisions based on ARAI range numbers — '
        'not real-world conditions. GenEV changes that.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            '<div style="background:#F8FAFC;border:1px solid #E2E8F0;'
            'border-radius:14px;padding:20px;text-align:center;height:180px;">'
            '<div style="font-size:32px;margin-bottom:10px;">🧪</div>'
            '<div style="font-size:14px;font-weight:600;color:#1E293B;'
            'margin-bottom:6px;">Realistic Simulation</div>'
            '<div style="font-size:12px;color:#64748B;line-height:1.6;">'
            'Simulate your EV in Delhi summer, monsoon traffic, '
            'or hilly terrain — in seconds.'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            '<div style="background:#F8FAFC;border:1px solid #E2E8F0;'
            'border-radius:14px;padding:20px;text-align:center;height:180px;">'
            '<div style="font-size:32px;margin-bottom:10px;">🤖</div>'
            '<div style="font-size:14px;font-weight:600;color:#1E293B;'
            'margin-bottom:6px;">AI-Powered Insights</div>'
            '<div style="font-size:12px;color:#64748B;line-height:1.6;">'
            'Ask why thermal risk was high, which EV suits your commute, '
            'and get grounded AI answers.'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            '<div style="background:#F8FAFC;border:1px solid #E2E8F0;'
            'border-radius:14px;padding:20px;text-align:center;height:180px;">'
            '<div style="font-size:32px;margin-bottom:10px;">📊</div>'
            '<div style="font-size:14px;font-weight:600;color:#1E293B;'
            'margin-bottom:6px;">6 Smart Metrics</div>'
            '<div style="font-size:12px;color:#64748B;line-height:1.6;">'
            'Efficiency, Battery Stress, Thermal Risk, Stability, '
            'Charging Efficiency — all scored and graded.'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── How It Works ──────────────────────────────────────────────────────────
    st.markdown(
        '<div style="text-align:center;margin-bottom:20px;">'
        '<div style="font-size:22px;font-weight:700;color:#1E293B;">'
        'How It Works</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    steps = [
        ("1", "Describe your scenario",
         "Type anything — 'Simulate EV in Delhi summer with fast charging'"),
        ("2", "AI parses and simulates",
         "Groq LLaMA extracts parameters and runs physics-based simulation"),
        ("3", "Get metrics and charts",
         "6 performance metrics, 6 telemetry charts, risk flags — instantly"),
        ("4", "Ask AI questions",
         "Chat with GenEV AI about your results using our RAG knowledge base"),
    ]

    cols = st.columns(4)
    for col, (num, title, desc) in zip(cols, steps):
        with col:
            st.markdown(
                f'<div style="text-align:center;padding:16px 8px;">'
                f'<div style="background:#1D9E75;color:white;border-radius:50%;'
                f'width:36px;height:36px;display:flex;align-items:center;'
                f'justify-content:center;font-size:16px;font-weight:700;'
                f'margin:0 auto 10px;">{num}</div>'
                f'<div style="font-size:13px;font-weight:600;color:#1E293B;'
                f'margin-bottom:6px;">{title}</div>'
                f'<div style="font-size:12px;color:#64748B;line-height:1.5;">'
                f'{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Indian EV Focus ───────────────────────────────────────────────────────
    st.markdown(
        '<div style="text-align:center;margin-bottom:16px;">'
        '<div style="font-size:22px;font-weight:700;color:#1E293B;">'
        '🇮🇳 Built for India</div>'
        '<div style="font-size:14px;color:#64748B;margin-top:6px;">'
        'Knowledge base covers Indian EVs, charging networks, subsidies and costs'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    evs = [
        ("🚗", "Tata Nexon EV",   "Most popular Indian EV"),
        ("🚗", "Tata Tiago EV",   "Most affordable EV"),
        ("🚗", "Tata Punch EV",   "Best-selling micro SUV EV"),
        ("🛵", "Ather 450X",      "Premium electric scooter"),
        ("🛵", "Ola S1 Pro",      "Performance scooter"),
        ("🚗", "MG Windsor EV",   "Battery-as-a-Service model"),
        ("🚗", "BYD Atto 3",      "Blade battery technology"),
        ("🚗", "Mahindra XEV 9e", "Flagship performance EV"),
    ]

    cols = st.columns(4)
    for i, (icon, name, desc) in enumerate(evs):
        with cols[i % 4]:
            st.markdown(
                f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;'
                f'border-radius:10px;padding:12px;margin-bottom:10px;'
                f'text-align:center;">'
                f'<div style="font-size:20px;">{icon}</div>'
                f'<div style="font-size:12px;font-weight:600;color:#1E293B;'
                f'margin-top:4px;">{name}</div>'
                f'<div style="font-size:11px;color:#64748B;">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Pricing Preview ───────────────────────────────────────────────────────
    st.markdown(
        '<div style="text-align:center;margin-bottom:20px;">'
        '<div style="font-size:22px;font-weight:700;color:#1E293B;">'
        'Simple Pricing</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            '<div style="display:flex;gap:12px;">'

            '<div style="flex:1;background:#F8FAFC;border:2px solid #E2E8F0;'
            'border-radius:14px;padding:20px;text-align:center;">'
            '<div style="font-size:15px;font-weight:700;color:#1E293B;'
            'margin-bottom:6px;">Free</div>'
            '<div style="font-size:28px;font-weight:800;color:#1D9E75;">₹0</div>'
            '<div style="font-size:11px;color:#64748B;margin-bottom:12px;">/forever</div>'
            '<div style="font-size:12px;color:#475569;text-align:left;line-height:1.8;">'
            '✓ 3 simulations/day<br>'
            '✓ All metrics & charts<br>'
            '✓ 1 AI question/day<br>'
            '✓ Scenario comparison<br>'
            '✓ Personal history'
            '</div>'
            '</div>'

            '<div style="flex:1;background:rgba(124,58,237,0.04);'
            'border:2px solid #7C3AED;'
            'border-radius:14px;padding:20px;text-align:center;">'
            '<div style="font-size:15px;font-weight:700;color:#7C3AED;'
            'margin-bottom:6px;">Premium ⭐</div>'
            '<div style="font-size:28px;font-weight:800;color:#7C3AED;">₹299</div>'
            '<div style="font-size:11px;color:#64748B;margin-bottom:12px;">/month</div>'
            '<div style="font-size:12px;color:#475569;text-align:left;line-height:1.8;">'
            '✓ Unlimited simulations<br>'
            '✓ 10 AI questions/day<br>'
            '✓ PDF report export<br>'
            '✓ Priority AI responses<br>'
            '✓ Advanced EV insights'
            '</div>'
            '</div>'

            '</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Final CTA ─────────────────────────────────────────────────────────────
    st.markdown(
        '<div style="text-align:center;padding:24px;background:rgba(29,158,117,0.06);'
        'border:1px solid rgba(29,158,117,0.20);border-radius:16px;margin-bottom:20px;">'
        '<div style="font-size:20px;font-weight:700;color:#1E293B;margin-bottom:8px;">'
        'Start simulating smarter EV decisions today</div>'
        '<div style="font-size:13px;color:#475569;margin-bottom:16px;">'
        'Free forever · No credit card needed · Built for India'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        final_cta = st.button(
            "⚡ Get Started Free",
            use_container_width=True,
            key="landing_final_cta",
        )

    if final_cta:
        st.session_state["show_auth"] = True
        st.rerun()

    st.divider()

    # ── Legal Disclaimer ──────────────────────────────────────────────────────
    st.markdown(
        '<div style="background:#F8FAFC;border:1px solid #E2E8F0;'
        'border-radius:12px;padding:20px 24px;margin-bottom:16px;">'
        '<div style="font-size:13px;font-weight:600;color:#1E293B;'
        'margin-bottom:10px;">⚖️ Legal & Disclaimers</div>'
        '<div style="font-size:12px;color:#64748B;line-height:1.8;">'
        '<strong>Simulation Disclaimer:</strong> GenEV simulations are synthetic models '
        'for educational and research purposes only. Results are not a substitute for '
        'real-world testing. Do not make critical purchasing or safety decisions based '
        'solely on GenEV simulation outputs.'
        '<br><br>'
        '<strong>AI Disclaimer:</strong> AI-generated insights are produced by large '
        'language models and may contain errors. Independently verify important claims '
        'before acting on them.'
        '<br><br>'
        '<strong>Jurisdiction:</strong> All legal matters, disputes, and suits arising '
        'from the use of GenEV are subject to the exclusive jurisdiction of the courts '
        'in <strong>Delhi, India</strong>. By using GenEV, you agree to this jurisdiction.'
        '<br><br>'
        '<strong>Data & Privacy:</strong> GenEV collects your email, name, and simulation '
        'data to provide the service. All data is stored securely with Row Level Security. '
        'We do not sell your data. By signing up, you agree to our Privacy Policy and '
        'Terms of Service.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Legal document expanders ──────────────────────────────────────────────
    with st.expander("🔐 Privacy Policy"):
        st.markdown("""
**Privacy Policy — GenEV** · *Last updated: June 2025*
**Jurisdiction: Delhi, India**

**What we collect:** Name, email, city, driving preferences, simulation data, chat history, and daily usage counts.

**How we use it:** To run the platform, personalise AI responses, enforce usage limits, and improve the product through anonymised analytics.

**Data security:** All data is stored on Supabase with Row Level Security (RLS) — no user can access another user's data. Passwords are never stored in plain text.

**Data sharing:** We do not sell or share your data. AI queries are processed by Groq in real-time and not permanently retained.

**Your rights:** You may request access, correction, or deletion of your data by emailing prathamahuja924@gmail.com. Deletion requests are fulfilled within 30 days.

**Contact:** Pratham Ahuja · prathamahuja924@gmail.com · Delhi, India
        """)

    with st.expander("📋 Terms of Service"):
        st.markdown("""
**Terms of Service — GenEV** · *Last updated: June 2025*
**Jurisdiction: Delhi, India — Governing law: Laws of India**

**1. Acceptance:** By using GenEV, you agree to these Terms. If you disagree, do not use the platform.

**2. Eligibility:** You must be at least 13 years of age to create an account.

**3. Acceptable Use:** You agree not to reverse-engineer the platform, abuse the AI system with spam, bypass subscription limits, impersonate other users, or use GenEV for unlawful purposes.

**4. Simulation Disclaimer:** Simulations are synthetic models for educational purposes only. They are not a substitute for real-world testing. GenEV is not liable for decisions made based on simulation outputs.

**5. AI Content:** AI responses may contain errors. Independently verify important claims.

**6. Intellectual Property:** The GenEV platform and brand are the intellectual property of Pratham Ahuja. You retain ownership of data you input.

**7. Termination:** We reserve the right to suspend accounts that violate these Terms without notice.

**8. Limitation of Liability:** GenEV and Pratham Ahuja are not liable for indirect, incidental, or consequential damages from using the platform.

**Contact:** Pratham Ahuja · prathamahuja924@gmail.com · Delhi, India
        """)

    with st.expander("🍪 Cookie Policy"):
        st.markdown("""
**Cookie Policy — GenEV** · *Last updated: June 2025*
**Jurisdiction: Delhi, India**

**Cookies we use:** GenEV uses only two essential session cookies — `genev_access_token` and `genev_refresh_token` — solely to keep you logged in across page refreshes and browser restores.

**No tracking:** We do not use advertising, analytics, or third-party tracking cookies of any kind.

**Security:** All cookies are AES-encrypted before being stored in your browser. They are never stored in plain text and are automatically cleared on logout.

**Managing cookies:** You can clear cookies at any time through your browser settings. Clearing cookies will log you out of GenEV.

**Consent:** By creating an account and using GenEV, you consent to our use of these essential session cookies.

**Contact:** Pratham Ahuja · prathamahuja924@gmail.com · Delhi, India
        """)

    with st.expander("💰 Refund Policy"):
        st.markdown("""
**Refund Policy — GenEV** · *Last updated: June 2025*
**Jurisdiction: Delhi, India**

**Free Plan:** No payment required. No refund applicable.

**Premium Plan (₹299/month):** Subscription fees are generally non-refundable once a billing period has begun, as you receive immediate access to all Premium features.

**Eligible refund cases:** Double charges, complete service unavailability for 72+ consecutive hours, verified technical failures preventing Premium access, or unauthorised charges.

**Non-eligible cases:** Change of mind, partial use, dissatisfaction with AI response quality, or failure to use the service.

**How to request:** Email prathamahuja924@gmail.com with subject "GenEV Refund Request" including your registered email, charge date, reason, and transaction ID. Requests must be submitted within 7 days of the charge.

**Processing:** Approved refunds are processed within 7–10 business days.

**Contact:** Pratham Ahuja · prathamahuja924@gmail.com · Delhi, India
        """)

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="text-align:center;padding:20px 16px 10px;">'
        f'<div style="font-size:11px;color:#94A3B8;line-height:2;">'
        f'Built by <strong style="color:#1D9E75;">Pratham Ahuja</strong> · '
        f'GenEV v{APP_VERSION} · AI-Powered EV Intelligence'
        f'<br>'
        f'<a href="mailto:prathamahuja924@gmail.com" '
        f'style="color:#1D9E75;text-decoration:none;">'
        f'prathamahuja924@gmail.com</a>'
        f' · All disputes subject to jurisdiction of courts in '
        f'<strong style="color:#475569;">Delhi, India</strong>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    return False