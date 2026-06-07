"""
frontend/components/about.py

About page, feedback form, bug reporting, roadmap,
legal documents, and creator identity for GenEV 2.0.
"""

import streamlit as st

from auth.auth_handler import get_user_id, get_user_name, is_premium
from database.supabase_client import save_feedback
from config import (
    APP_VERSION,
    CREATOR_NAME,
    CREATOR_EMAIL,
    CREATOR_LINKEDIN,
    CREATOR_GITHUB,
    PREMIUM_PRICE_INR,
)


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def render_about_page() -> None:
    """Render the complete about page."""

    st.markdown(
        '<div style="text-align:center;padding:20px 0 10px;">'
        '<div style="font-size:48px;margin-bottom:8px;">⚡</div>'
        '<div style="font-size:28px;font-weight:800;color:#1D9E75;">'
        'GenEV</div>'
        '<div style="font-size:14px;color:#475569;margin-top:4px;">'
        f'AI-Powered EV Ownership Intelligence Platform · v{APP_VERSION}'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.divider()
    _render_mission()
    st.divider()
    _render_how_it_works()
    st.divider()
    _render_features()
    st.divider()
    _render_tech_stack()
    st.divider()
    _render_roadmap()
    st.divider()
    _render_feedback_section()
    st.divider()
    _render_legal_section()
    st.divider()
    _render_creator()


# ─────────────────────────────────────────────────────────────────────────────
# Mission
# ─────────────────────────────────────────────────────────────────────────────

def _render_mission() -> None:
    st.markdown("### 🎯 Our Mission")

    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown(
            '<div style="font-size:14px;color:#1E293B;line-height:1.9;">'
            'GenEV was built to solve a real problem: <strong>most EV buyers '
            'in India make decisions based on ARAI range numbers and showroom '
            'demos</strong> — not real-world operating conditions.'
            '<br><br>'
            'GenEV simulates what actually happens when you drive your EV in '
            '<strong>Delhi summer traffic</strong>, charge repeatedly with a '
            '<strong>DC fast charger</strong>, or drive on '
            '<strong>hilly terrain in monsoon</strong>.'
            '<br><br>'
            'Then our AI explains <em>why</em> it happened — and what you '
            'should do about it.'
            '</div>',
            unsafe_allow_html=True,
        )

    with col2:
        stats = [
            ("7+",  "Indian EV models in knowledge base"),
            ("6",   "Performance metrics computed"),
            ("4",   "Knowledge base documents"),
            ("97+", "RAG knowledge chunks indexed"),
        ]
        for value, label in stats:
            st.markdown(
                f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;'
                f'border-radius:12px;padding:14px 16px;margin-bottom:10px;'
                f'text-align:center;">'
                f'<div style="font-size:28px;font-weight:800;color:#1D9E75;">'
                f'{value}</div>'
                f'<div style="font-size:12px;color:#64748B;margin-top:2px;">'
                f'{label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# How it works
# ─────────────────────────────────────────────────────────────────────────────

def _render_how_it_works() -> None:
    st.markdown("### 🧠 How GenEV Works")

    steps = [
        ("1", "🗣️", "Natural Language Input",
         "Describe any EV scenario in plain English — "
         "GenEV understands context like 'Delhi summer' or 'hilly terrain'."),
        ("2", "🤖", "LLM Scenario Parsing",
         "Groq LLaMA 3.3 70B extracts structured simulation parameters "
         "from your natural language description."),
        ("3", "📡", "Synthetic Telemetry Generation",
         "NumPy-powered physics engine generates realistic time-series data "
         "using Peukert's law, Arrhenius thermal model, and Monte Carlo noise."),
        ("4", "⚙️", "EV Simulation Engine",
         "Battery dynamics, thermal behavior, charging physics, "
         "and regenerative braking are simulated step by step."),
        ("5", "📊", "Metric Evaluation",
         "6 metrics quantify efficiency, battery stress, thermal risk, "
         "stability, charging efficiency, and AI optimisation gain."),
        ("6", "🔍", "RAG Knowledge Retrieval",
         "ChromaDB + sentence-transformers retrieve relevant EV knowledge "
         "chunks semantically matched to your question."),
        ("7", "💬", "Contextual AI Response",
         "Groq combines retrieved knowledge + your simulation results "
         "to generate grounded, data-driven explanations."),
    ]

    for num, icon, title, desc in steps:
        st.markdown(
            f'<div style="display:flex;gap:16px;align-items:flex-start;'
            f'margin-bottom:14px;padding:14px;background:#F8FAFC;'
            f'border:1px solid #E2E8F0;border-radius:12px;">'
            f'<div style="background:#1D9E75;color:white;border-radius:50%;'
            f'width:32px;height:32px;display:flex;align-items:center;'
            f'justify-content:center;font-size:13px;font-weight:700;'
            f'flex-shrink:0;">{num}</div>'
            f'<div>'
            f'<div style="font-size:14px;font-weight:600;color:#1E293B;'
            f'margin-bottom:3px;">{icon} {title}</div>'
            f'<div style="font-size:13px;color:#475569;line-height:1.5;">'
            f'{desc}</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Features
# ─────────────────────────────────────────────────────────────────────────────

def _render_features() -> None:
    st.markdown("### ✨ Core Features")

    features = [
        {
            "icon":      "🧪",
            "title":     "EV Scenario Simulation",
            "desc":      "Simulate any EV operating condition from natural language. "
                         "Delhi summer traffic, monsoon driving, highway cruising — "
                         "all powered by physics-based modelling.",
            "tag":       "Free",
            "tag_color": "#1D9E75",
        },
        {
            "icon":      "📊",
            "title":     "6-Metric Performance Dashboard",
            "desc":      "Efficiency Score, Battery Stress Index, Thermal Risk, "
                         "Stability Score, Charging Efficiency, and AI Optimisation "
                         "Gain — with letter grades and risk flags.",
            "tag":       "Free",
            "tag_color": "#1D9E75",
        },
        {
            "icon":      "🤖",
            "title":     "Contextual RAG AI Chat",
            "desc":      "Ask why thermal risk was high, which EV suits your commute, "
                         "or how charging frequency affects degradation. AI answers "
                         "grounded in your simulation + EV knowledge base.",
            "tag":       "Free (1/day) · Premium (10/day)",
            "tag_color": "#7C3AED",
        },
        {
            "icon":      "🔀",
            "title":     "Scenario Comparison",
            "desc":      "Compare up to 4 simulation runs side by side. "
                         "Metric diff tables, telemetry overlays, and category "
                         "winners help you find the optimal EV strategy.",
            "tag":       "Free",
            "tag_color": "#1D9E75",
        },
        {
            "icon":      "📄",
            "title":     "PDF Report Export",
            "desc":      "Download a branded, professional simulation report "
                         "with metrics, risk flags, AI insights, and trip summary. "
                         "Perfect for sharing and presentations.",
            "tag":       "Premium",
            "tag_color": "#7C3AED",
        },
        {
            "icon":      "📜",
            "title":     "Personal Simulation History",
            "desc":      "Every simulation is saved privately to your account. "
                         "Load, compare, and delete past runs. "
                         "Your data is never visible to other users.",
            "tag":       "Free",
            "tag_color": "#1D9E75",
        },
    ]

    col1, col2 = st.columns(2)
    cols = [col1, col2, col1, col2, col1, col2]

    for col, feature in zip(cols, features):
        with col:
            st.markdown(
                f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;'
                f'border-radius:12px;padding:16px;margin-bottom:12px;">'
                f'<div style="display:flex;justify-content:space-between;'
                f'align-items:flex-start;margin-bottom:8px;">'
                f'<div style="font-size:22px;">{feature["icon"]}</div>'
                f'<span style="background:rgba(29,158,117,0.08);'
                f'color:{feature["tag_color"]};font-size:10px;font-weight:600;'
                f'padding:2px 8px;border-radius:20px;">{feature["tag"]}</span>'
                f'</div>'
                f'<div style="font-size:13px;font-weight:600;color:#1E293B;'
                f'margin-bottom:6px;">{feature["title"]}</div>'
                f'<div style="font-size:12px;color:#475569;line-height:1.6;">'
                f'{feature["desc"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# Tech stack
# ─────────────────────────────────────────────────────────────────────────────

def _render_tech_stack() -> None:
    st.markdown("### 🛠️ Built With")

    stack = [
        ("🤖", "Groq LLaMA 3.3 70B",   "LLM for scenario parsing and AI insights"),
        ("🔍", "ChromaDB",              "Vector database for semantic search"),
        ("🧬", "Sentence Transformers", "Local embeddings (all-MiniLM-L6-v2)"),
        ("🌐", "Streamlit",             "Interactive web frontend"),
        ("📊", "Plotly",                "Interactive data visualisation"),
        ("🔢", "NumPy",                 "Physics simulation and telemetry"),
        ("🗄️", "Supabase",             "Auth, database, row-level security"),
        ("📄", "ReportLab",             "PDF report generation"),
        ("🐍", "Python 3.11",           "Core language"),
    ]

    cols = st.columns(3)
    for i, (icon, name, desc) in enumerate(stack):
        with cols[i % 3]:
            st.markdown(
                f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;'
                f'border-radius:10px;padding:12px;margin-bottom:10px;">'
                f'<div style="font-size:18px;margin-bottom:4px;">{icon}</div>'
                f'<div style="font-size:12px;font-weight:600;color:#1E293B;">'
                f'{name}</div>'
                f'<div style="font-size:11px;color:#64748B;margin-top:2px;">'
                f'{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# Roadmap
# ─────────────────────────────────────────────────────────────────────────────

def _render_roadmap() -> None:
    st.markdown("### 🗺️ Product Roadmap")

    roadmap = [
        {
            "phase": "v2.0 — Current",
            "color": "#1D9E75",
            "bg":    "#E1F5EE",
            "items": [
                "✅ User authentication with Supabase",
                "✅ RAG-powered AI chat",
                "✅ PDF report export",
                "✅ Personal simulation history",
                "✅ Scenario comparison",
                "✅ Subscription system",
            ],
        },
        {
            "phase": "v2.1 — Coming Soon",
            "color": "#2563EB",
            "bg":    "#DBEAFE",
            "items": [
                "🔄 Razorpay payment integration",
                "🔄 Real charging station map integration",
                "🔄 EV recommendation engine",
                "🔄 Fleet simulation mode",
                "🔄 Mobile app (React Native)",
            ],
        },
        {
            "phase": "v3.0 — Future Vision",
            "color": "#7C3AED",
            "bg":    "#EDE9FE",
            "items": [
                "🚀 Battery health prediction (ML model)",
                "🚀 Real-time telematics integration",
                "🚀 Multimodal scenario input (voice)",
                "🚀 Vehicle-to-Grid (V2G) simulation",
                "🚀 Pan-India charging route planner",
            ],
        },
    ]

    cols = st.columns(3)
    for col, phase_data in zip(cols, roadmap):
        with col:
            items_html = "".join([
                f'<div style="font-size:12px;color:#1E293B;'
                f'margin-bottom:6px;line-height:1.4;">{item}</div>'
                for item in phase_data["items"]
            ])
            st.markdown(
                f'<div style="background:{phase_data["bg"]};'
                f'border:1px solid {phase_data["color"]}40;'
                f'border-radius:12px;padding:16px;">'
                f'<div style="font-size:13px;font-weight:700;'
                f'color:{phase_data["color"]};margin-bottom:12px;">'
                f'{phase_data["phase"]}</div>'
                f'{items_html}'
                f'</div>',
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# Feedback section
# ─────────────────────────────────────────────────────────────────────────────

def _render_feedback_section() -> None:
    st.markdown("### 💬 Feedback & Bug Reports")
    st.markdown(
        "<p style='color:#64748B;font-size:13px;margin-bottom:16px;'>"
        "Help us improve GenEV. Your feedback shapes the product.</p>",
        unsafe_allow_html=True,
    )

    tab1, tab2 = st.tabs(["💡 Share Feedback", "🐛 Report a Bug"])

    with tab1:
        _render_feedback_form()

    with tab2:
        _render_bug_form()


def _render_feedback_form() -> None:
    user_id = get_user_id()

    with st.form("feedback_form", clear_on_submit=True):
        feedback_type = st.selectbox(
            "Feedback Type",
            options=[
                "Feature Request",
                "General Feedback",
                "Simulation Accuracy",
                "AI Response Quality",
                "UI/UX Suggestion",
                "Other",
            ],
        )
        message = st.text_area(
            "Your Feedback",
            placeholder="Tell us what you think, what's missing, "
                        "or what you'd like to see...",
            height=120,
        )
        submitted = st.form_submit_button("Submit Feedback →")

    if submitted:
        if not message.strip():
            st.warning("Please enter your feedback.", icon="⚠️")
            return
        if not user_id:
            st.warning("Please log in to submit feedback.", icon="⚠️")
            return
        try:
            save_feedback(
                user_id=user_id,
                feedback_type=feedback_type,
                message=message.strip(),
                severity="low",
            )
            st.success("Thank you! Your feedback has been recorded.", icon="✅")
        except Exception as e:
            st.error(f"Could not save feedback: {e}", icon="🔴")


def _render_bug_form() -> None:
    user_id = get_user_id()

    with st.form("bug_form", clear_on_submit=True):
        severity = st.selectbox(
            "Severity",
            options=["Low", "Medium", "High", "Critical"],
        )
        description = st.text_area(
            "Bug Description",
            placeholder="Describe what happened, what you expected, "
                        "and steps to reproduce...",
            height=120,
        )
        submitted = st.form_submit_button("Report Bug →")

    if submitted:
        if not description.strip():
            st.warning("Please describe the bug.", icon="⚠️")
            return
        if not user_id:
            st.warning("Please log in to report bugs.", icon="⚠️")
            return
        try:
            save_feedback(
                user_id=user_id,
                feedback_type="Bug Report",
                message=description.strip(),
                severity=severity.lower(),
            )
            st.success("Bug reported successfully. Thank you!", icon="✅")
        except Exception as e:
            st.error(f"Could not save bug report: {e}", icon="🔴")


# ─────────────────────────────────────────────────────────────────────────────
# Legal section
# ─────────────────────────────────────────────────────────────────────────────

def _render_legal_section() -> None:
    """Legal documents — Privacy Policy, Terms, Cookie Policy, Refund Policy."""
    st.markdown("### ⚖️ Legal")
    st.markdown(
        "<p style='color:#64748B;font-size:13px;margin-bottom:16px;'>"
        "Please read these documents before using GenEV.</p>",
        unsafe_allow_html=True,
    )

    tab1, tab2, tab3, tab4 = st.tabs([
        "🔐 Privacy Policy",
        "📋 Terms of Service",
        "🍪 Cookie Policy",
        "💰 Refund Policy",
    ])

    with tab1:
        _render_privacy_policy()

    with tab2:
        _render_terms_of_service()

    with tab3:
        _render_cookie_policy()

    with tab4:
        _render_refund_policy()


def _render_privacy_policy() -> None:
    st.markdown("""
**Privacy Policy — GenEV**
*Last updated: June 2025*

**Jurisdiction:** All disputes arising out of or in connection with this Privacy Policy
shall be subject to the exclusive jurisdiction of the courts in **Delhi, India**.

---

**1. Information We Collect**

When you use GenEV, we collect:
- **Account Information:** Your name, email address, and password (stored securely via Supabase Auth)
- **Profile Information:** City, daily commute distance, driving style, and home charging access — used to personalise AI recommendations
- **Simulation Data:** Your simulation prompts, results, metrics, and telemetry — stored privately and isolated per user
- **Chat History:** Questions you ask the AI and the responses received
- **Usage Data:** Number of simulations and AI questions used per day

**2. How We Use Your Information**

- To provide and operate the GenEV platform
- To personalise AI simulation recommendations based on your profile
- To enforce subscription limits (Free vs Premium)
- To improve the platform through anonymised usage analytics
- To respond to feedback and bug reports you submit

**3. Data Storage and Security**

- All data is stored on **Supabase** (PostgreSQL) with **Row Level Security (RLS)**
- RLS ensures each user can only access their own data — no user can view another user's simulations, chat history, or profile
- Passwords are hashed and never stored in plain text
- Data is stored on Supabase-managed servers in secure cloud infrastructure

**4. Data Sharing**

We do **not** sell, rent, or share your personal data with third parties for marketing purposes.

Data may be shared only:
- With **Groq** (for AI query processing) — queries are processed in real-time and not permanently stored by Groq
- As required by law or court order

**5. Data Retention**

- Your account data is retained as long as your account is active
- You may request deletion of your account and all associated data by emailing **prathamahuja924@gmail.com**
- Deleted data is removed within 30 days

**6. Your Rights**

You have the right to:
- Access your personal data
- Correct inaccurate data
- Request deletion of your data
- Withdraw consent at any time

To exercise these rights, contact: **prathamahuja924@gmail.com**

**7. Contact**

Pratham Ahuja · prathamahuja924@gmail.com · Delhi, India
""")


def _render_terms_of_service() -> None:
    st.markdown("""
**Terms of Service — GenEV**
*Last updated: June 2025*

**Jurisdiction:** These Terms of Service shall be governed by and construed in
accordance with the laws of India. Any disputes arising hereunder shall be subject
to the exclusive jurisdiction of the courts in **Delhi, India**.

---

**1. Acceptance of Terms**

By creating an account or using the GenEV platform, you agree to be bound by these Terms of Service.
If you do not agree, you must not use the platform.

**2. Description of Service**

GenEV is an AI-powered EV simulation platform that allows users to:
- Simulate electric vehicle scenarios using natural language
- Analyse performance metrics and telemetry
- Ask AI-powered questions about EV ownership in India
- Export simulation reports (Premium feature)

**3. User Accounts**

- You must provide accurate information when creating an account
- You are responsible for maintaining the security of your account credentials
- You must not share your account with others
- You must be at least 13 years of age to use GenEV

**4. Acceptable Use**

You agree not to:
- Use GenEV for any unlawful purpose
- Attempt to reverse-engineer, scrape, or copy the platform
- Abuse the AI chat system with spam or malicious queries
- Attempt to bypass subscription limits through technical means
- Impersonate other users or misrepresent your identity

**5. Subscription and Payments**

- The Free plan is provided at no cost with usage limits (3 simulations/day, 1 AI question/day)
- The Premium plan (₹299/month) provides expanded limits and additional features
- Subscription fees are non-refundable except as described in the Refund Policy
- GenEV reserves the right to modify pricing with 30 days notice

**6. Simulation Accuracy Disclaimer**

GenEV simulations are **synthetic models** based on physics principles and publicly available EV data.
They are intended for **educational and research purposes only**.

- Simulation results are not a substitute for real-world testing
- GenEV does not guarantee accuracy of simulated metrics
- Do not make critical purchasing or safety decisions based solely on GenEV simulations
- GenEV is not liable for any decisions made based on simulation outputs

**7. AI-Generated Content**

- AI responses are generated by large language models and may contain errors
- GenEV does not guarantee the accuracy of AI-generated insights
- Users should independently verify important claims before acting on them

**8. Intellectual Property**

- The GenEV platform, codebase, and brand are the intellectual property of Pratham Ahuja
- Users retain ownership of data they input into the platform
- GenEV retains the right to use anonymised, aggregated usage data for platform improvement

**9. Termination**

GenEV reserves the right to terminate or suspend accounts that violate these Terms,
without notice and at our sole discretion.

**10. Limitation of Liability**

To the maximum extent permitted by applicable law, GenEV and Pratham Ahuja shall not
be liable for any indirect, incidental, special, or consequential damages arising from
the use of or inability to use the platform.

**11. Changes to Terms**

We reserve the right to modify these Terms at any time. Continued use of the platform
after changes constitutes acceptance of the new Terms.

**12. Contact**

Pratham Ahuja · prathamahuja924@gmail.com · Delhi, India
""")


def _render_cookie_policy() -> None:
    st.markdown("""
**Cookie Policy — GenEV**
*Last updated: June 2025*

**Jurisdiction:** This Cookie Policy is governed by the laws of India.
Any disputes shall be subject to the exclusive jurisdiction of courts in **Delhi, India**.

---

**1. What Are Cookies**

Cookies are small text files stored in your browser that allow websites to remember
information about your visit. GenEV uses cookies solely for functional purposes.

**2. Cookies We Use**

GenEV uses **only essential cookies** — no advertising or tracking cookies.

| Cookie | Purpose | Duration |
|--------|---------|----------|
| `genev_access_token` | Stores your encrypted login session token to keep you logged in | Until logout or expiry |
| `genev_refresh_token` | Allows automatic session renewal without re-login | Until logout or expiry |

**3. Why We Use These Cookies**

These cookies are strictly necessary to:
- Keep you logged in across page refreshes
- Restore your session when you reopen the browser
- Maintain secure authentication with our Supabase backend

**4. No Third-Party Cookies**

GenEV does not use:
- Advertising cookies
- Social media tracking cookies
- Analytics tracking cookies (e.g., Google Analytics)
- Any third-party cookies

**5. Cookie Security**

All session cookies are:
- **Encrypted** using AES encryption before being stored in your browser
- **Never stored in plain text**
- Automatically invalidated when you log out

**6. Managing Cookies**

You can clear cookies at any time through your browser settings.
Clearing cookies will log you out of GenEV and you will need to sign in again.

**7. Consent**

By using GenEV and creating an account, you consent to our use of essential session cookies
as described in this policy.

**8. Contact**

Pratham Ahuja · prathamahuja924@gmail.com · Delhi, India
""")


def _render_refund_policy() -> None:
    st.markdown("""
**Refund Policy — GenEV**
*Last updated: June 2025*

**Jurisdiction:** This Refund Policy is governed by the laws of India.
Any disputes shall be subject to the exclusive jurisdiction of courts in **Delhi, India**.

---

**1. Free Plan**

The GenEV Free plan is provided at no charge. No payment is required and therefore
no refund applies.

**2. Premium Plan — General Policy**

GenEV Premium subscriptions are billed at ₹299/month.

As a general rule, **subscription fees are non-refundable** once a billing period has commenced,
as you receive immediate access to all Premium features upon payment.

**3. Eligible Refund Cases**

Refunds will be considered in the following circumstances:

- **Double charge:** You were charged twice for the same billing period
- **Service unavailability:** GenEV Premium was completely unavailable for more than 72 consecutive hours during your billing period
- **Technical failure:** A verified technical error on our end prevented you from accessing Premium features
- **Unauthorised charge:** A charge was made to your account without your authorisation

**4. Non-Eligible Cases**

Refunds will **not** be issued for:
- Change of mind after purchase
- Partial use of the subscription period
- Dissatisfaction with AI response quality (AI-generated content is inherently variable)
- Failure to use the service during the subscription period
- Incompatibility with your device or browser

**5. How to Request a Refund**

To request a refund, email us at **prathamahuja924@gmail.com** with:
- Subject: "GenEV Refund Request"
- Your registered email address
- Date of charge
- Reason for refund request
- Transaction ID or payment reference

Refund requests must be submitted within **7 days** of the charge date.

**6. Processing Time**

Approved refunds will be processed within **7–10 business days** to your original payment method.

**7. Contact**

Pratham Ahuja · prathamahuja924@gmail.com · Delhi, India
""")


# ─────────────────────────────────────────────────────────────────────────────
# Creator
# ─────────────────────────────────────────────────────────────────────────────

def _render_creator() -> None:
    st.markdown("### 👨‍💻 About the Creator")

    col1, col2 = st.columns([2, 3])

    with col1:
        st.markdown(
            '<div style="background:linear-gradient(135deg,'
            'rgba(29,158,117,0.08),rgba(37,99,235,0.08));'
            'border:1px solid rgba(29,158,117,0.20);'
            'border-radius:16px;padding:24px;text-align:center;">'
            '<div style="font-size:48px;margin-bottom:8px;">👨‍💻</div>'
            f'<div style="font-size:18px;font-weight:700;color:#1E293B;'
            f'margin-bottom:4px;">{CREATOR_NAME}</div>'
            '<div style="font-size:12px;color:#64748B;margin-bottom:14px;">'
            'AI & Data Science Undergraduate'
            '</div>'
            '<div style="display:flex;flex-direction:column;gap:8px;">'
            f'<a href="mailto:{CREATOR_EMAIL}" style="background:#1D9E75;'
            f'color:white;padding:8px 16px;border-radius:8px;'
            f'text-decoration:none;font-size:12px;font-weight:600;">'
            f'📧 Email</a>'
            f'<a href="{CREATOR_LINKEDIN}" target="_blank" '
            f'style="background:#2563EB;color:white;padding:8px 16px;'
            f'border-radius:8px;text-decoration:none;font-size:12px;'
            f'font-weight:600;">💼 LinkedIn</a>'
            f'<a href="{CREATOR_GITHUB}" target="_blank" '
            f'style="background:#1E293B;color:white;padding:8px 16px;'
            f'border-radius:8px;text-decoration:none;font-size:12px;'
            f'font-weight:600;">🐙 GitHub</a>'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            '<div style="font-size:14px;color:#1E293B;line-height:1.9;">'
            f'Hi, I\'m <strong>{CREATOR_NAME}</strong> — an AI & Data Science '
            'undergraduate passionate about building intelligent systems '
            'that solve real-world problems.'
            '<br><br>'
            '<strong>GenEV</strong> was built as a demonstration of '
            'modern AI systems engineering — combining generative AI, '
            'retrieval-augmented generation, physics simulation, and '
            'SaaS product design into a single coherent platform.'
            '<br><br>'
            '<strong>Technical Focus Areas:</strong>'
            '</div>',
            unsafe_allow_html=True,
        )

        focus_areas = [
            "🤖 AI Systems Engineering",
            "🔍 Retrieval-Augmented Generation (RAG)",
            "💬 Conversational AI Platforms",
            "📊 Intelligent Simulation Frameworks",
            "🚀 AI SaaS Product Design",
            "🔢 Synthetic Data Engineering",
        ]

        for area in focus_areas:
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;'
                f'margin-bottom:6px;">'
                f'<span style="color:#1D9E75;font-size:14px;">→</span>'
                f'<span style="font-size:13px;color:#1E293B;">{area}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown(
            '<div style="margin-top:14px;padding:12px 16px;'
            'background:#F8FAFC;border-left:3px solid #1D9E75;'
            'border-radius:6px;font-size:13px;color:#475569;'
            'font-style:italic;line-height:1.6;">'
            '"GenEV demonstrates that AI systems engineering goes beyond '
            'training models — it\'s about architecting intelligent platforms '
            'that combine multiple AI technologies into production-grade '
            'user experiences."'
            '</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<div style="text-align:center;padding:20px;margin-top:10px;">'
        f'<div style="font-size:12px;color:#94A3B8;">'
        f'Built by <strong style="color:#1D9E75;">{CREATOR_NAME}</strong> · '
        f'GenEV v{APP_VERSION} · '
        f'<a href="mailto:{CREATOR_EMAIL}" '
        f'style="color:#1D9E75;text-decoration:none;">{CREATOR_EMAIL}</a>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )