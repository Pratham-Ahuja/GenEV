"""
frontend/components/ai_chat.py

RAG-powered conversational AI chat UI for GenEV 2.0.

Features
--------
- ChatGPT-style message interface
- Simulation context memory
- Question limit display
- Source citations from knowledge base
- Upgrade prompt for free users
- Chat history from Supabase
- Clear chat functionality
"""

import re
import streamlit as st

from auth.auth_handler import (
    get_user_id,
    is_premium,
)
from rag.rag_engine import get_rag_engine
from database.supabase_client import (
    get_chat_history,
    clear_chat_history,
    check_question_limit,
)


# ─────────────────────────────────────────────────────────────────────────────
# Source label map
# ─────────────────────────────────────────────────────────────────────────────

_SOURCE_LABELS = {
    "indian_ev_specs":    "🚗 Indian EV Specs",
    "battery_knowledge":  "🔋 Battery Science",
    "charging_guide":     "🔌 Charging Guide",
    "ev_ownership_india": "📋 EV Ownership India",
}


def _format_source(source: str) -> str:
    return _SOURCE_LABELS.get(
        source,
        f"📚 {source.replace('_', ' ').title()}"
    )


def _ensure_chat_list() -> None:
    """
    Guarantee st.session_state.chat_messages is always a list.
    Handles None, missing key, and wrong type all in one place.
    """
    if not isinstance(st.session_state.get("chat_messages"), list):
        st.session_state.chat_messages = []


# ─────────────────────────────────────────────────────────────────────────────
# Main render function
# ─────────────────────────────────────────────────────────────────────────────

def render_ai_chat(simulation_context: dict = None) -> None:
    """
    Render the full AI chat interface.

    Parameters
    ----------
    simulation_context : dict
        The most recent simulation result + metrics dict.
        Passed from app.py session state.
        If None, AI will answer from knowledge base only.
    """
    user_id = get_user_id()
    if not user_id:
        st.warning("Please log in to use AI Chat.", icon="⚠️")
        return

    # ── Ensure chat list is valid on every render ─────────────────────────────
    _ensure_chat_list()

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("## 🤖 GenEV AI Chat")
    st.markdown(
        "<p style='color:#64748B;font-size:13px;margin-bottom:4px;'>"
        "Ask anything about your simulation results, EV specs, "
        "battery science, or Indian EV ownership.</p>",
        unsafe_allow_html=True,
    )

    # ── Simulation context banner ─────────────────────────────────────────────
    if simulation_context:
        label   = simulation_context.get("scenario_label", "Recent simulation")
        overall = simulation_context.get("metrics", {}).get("overall_score", 0)
        st.markdown(
            f'<div style="background:rgba(29,158,117,0.08);border:1px solid '
            f'rgba(29,158,117,0.25);border-radius:10px;padding:10px 14px;'
            f'margin-bottom:12px;font-size:13px;color:#1E293B;">'
            f'<span style="color:#1D9E75;font-weight:600;">⚡ Active Context:</span> '
            f'{label} · Overall Score: <strong>{overall:.1f}/100</strong>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="background:#FEF3C7;border:1px solid #D97706;'
            'border-radius:10px;padding:10px 14px;margin-bottom:12px;'
            'font-size:13px;color:#1E293B;">'
            '💡 <strong>Tip:</strong> Run a simulation first for '
            'context-aware AI answers about your specific scenario.'
            '</div>',
            unsafe_allow_html=True,
        )

    # ── Question limit display ────────────────────────────────────────────────
    _render_question_limit_bar(user_id)

    st.divider()

    # ── Chat history ──────────────────────────────────────────────────────────
    _render_chat_history(user_id)

    # ── Input area ────────────────────────────────────────────────────────────
    _render_chat_input(user_id, simulation_context)

    # ── Suggested questions ───────────────────────────────────────────────────
    _render_suggested_questions(simulation_context)


# ─────────────────────────────────────────────────────────────────────────────
# Question limit bar
# ─────────────────────────────────────────────────────────────────────────────

def _render_question_limit_bar(user_id: str) -> None:
    """Render question usage progress bar."""
    allowed, used, limit = check_question_limit(user_id)
    premium = is_premium()

    if premium:
        label_color = "#1D9E75"
    elif used >= limit:
        label_color = "#DC2626"
    else:
        label_color = "#D97706"

    pct       = min(100, int((used / limit) * 100)) if limit > 0 else 100
    bar_color = label_color

    st.markdown(
        f'<div style="margin-bottom:8px;">'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;margin-bottom:4px;">'
        f'<span style="font-size:12px;color:#64748B;">AI Questions Today</span>'
        f'<span style="font-size:12px;font-weight:600;color:{label_color};">'
        f'{used}/{limit} used</span>'
        f'</div>'
        f'<div style="background:#E2E8F0;border-radius:4px;height:6px;">'
        f'<div style="background:{bar_color};height:6px;border-radius:4px;'
        f'width:{pct}%;transition:width 0.3s;"></div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if not allowed and not premium:
        st.markdown(
            '<div style="background:#FEE2E2;border:1px solid #DC2626;'
            'border-radius:10px;padding:12px 16px;margin-top:8px;">'
            '<div style="font-size:13px;font-weight:600;color:#DC2626;'
            'margin-bottom:4px;">Daily limit reached</div>'
            '<div style="font-size:12px;color:#1E293B;">'
            'Upgrade to <strong>GenEV Premium</strong> for 10 AI questions/day, '
            'PDF exports, and advanced insights. '
            'Your free limit resets tomorrow.</div>'
            '</div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Chat history display
# ─────────────────────────────────────────────────────────────────────────────

def _render_chat_history(user_id: str) -> None:
    """Render chat message history."""

    # Load from Supabase only on first render (when list is empty)
    if isinstance(st.session_state.get("chat_messages"), list) and \
       len(st.session_state.chat_messages) == 0:
        try:
            history = get_chat_history(user_id, limit=20)
            for msg in history:
                if msg.get("question"):
                    st.session_state.chat_messages.append({
                        "role":    "user",
                        "content": msg["question"],
                        "sources": [],
                        "time":    msg.get("created_at", ""),
                    })
                if msg.get("answer"):
                    st.session_state.chat_messages.append({
                        "role":    "assistant",
                        "content": msg["answer"],
                        "sources": msg.get("sources", []),
                        "time":    msg.get("created_at", ""),
                    })
        except Exception:
            pass

    # Chat container
    with st.container():
        if not st.session_state.chat_messages:
            _render_empty_chat_state()
        else:
            for msg in st.session_state.chat_messages:
                _render_message(msg)

    # Clear chat button
    if st.session_state.chat_messages:
        col1, col2 = st.columns([6, 1])
        with col2:
            if st.button(
                "🗑️ Clear",
                key="clear_chat",
                use_container_width=True,
                help="Clear chat history",
            ):
                try:
                    clear_chat_history(user_id)
                except Exception:
                    pass
                st.session_state.chat_messages = []
                st.rerun()


def _render_empty_chat_state() -> None:
    """Render empty state when no messages exist."""
    st.markdown(
        '<div style="text-align:center;padding:40px 20px;color:#94A3B8;">'
        '<div style="font-size:36px;margin-bottom:12px;">🤖</div>'
        '<div style="font-size:15px;font-weight:600;color:#475569;'
        'margin-bottom:8px;">GenEV AI is ready</div>'
        '<div style="font-size:13px;line-height:1.7;">'
        'Ask me anything about your simulation,<br>'
        'Indian EV models, battery science,<br>'
        'or EV ownership in India.</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _render_message(msg: dict) -> None:
    """Render a single chat message."""
    role    = msg.get("role", "user")
    content = msg.get("content", "")
    sources = msg.get("sources", [])

    if role == "user":
        st.markdown(
            f'<div style="display:flex;justify-content:flex-end;'
            f'margin-bottom:8px;">'
            f'<div style="background:#1D9E75;color:white;'
            f'border-radius:16px 16px 4px 16px;'
            f'padding:10px 16px;max-width:80%;font-size:13px;line-height:1.5;">'
            f'{content}'
            f'</div></div>',
            unsafe_allow_html=True,
        )
    else:
        formatted = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', content)
        formatted = formatted.replace("\n", "<br>")

        sources_html = ""
        if sources:
            source_badges = "".join([
                f'<span style="background:#F0FDF4;color:#1D9E75;font-size:10px;'
                f'padding:2px 8px;border-radius:20px;margin-right:4px;'
                f'border:1px solid #BBF7D0;">{_format_source(s)}</span>'
                for s in sources
            ])
            sources_html = (
                f'<div style="margin-top:8px;padding-top:6px;'
                f'border-top:1px solid #E2E8F0;">'
                f'<span style="font-size:10px;color:#94A3B8;margin-right:6px;">'
                f'Sources:</span>{source_badges}</div>'
            )

        st.markdown(
            f'<div style="display:flex;justify-content:flex-start;'
            f'margin-bottom:8px;">'
            f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;'
            f'border-radius:16px 16px 16px 4px;padding:10px 16px;'
            f'max-width:85%;font-size:13px;line-height:1.5;color:#1E293B;">'
            f'<div style="font-size:10px;color:#1D9E75;font-weight:600;'
            f'margin-bottom:4px;">⚡ GenEV AI</div>'
            f'{formatted}'
            f'{sources_html}'
            f'</div></div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Chat input
# ─────────────────────────────────────────────────────────────────────────────

def _render_chat_input(
    user_id: str,
    simulation_context: dict = None,
) -> None:
    """Render the chat input box and send button."""
    allowed, used, limit = check_question_limit(user_id)

    if not allowed:
        st.text_input(
            "Ask GenEV AI...",
            placeholder="Daily question limit reached. Upgrade for more.",
            disabled=True,
            label_visibility="collapsed",
        )
        return

    col_input, col_send = st.columns([6, 1])

    with col_input:
        question = st.text_input(
            "Ask GenEV AI...",
            placeholder="e.g. Why was thermal risk high in my simulation?",
            label_visibility="collapsed",
            key="chat_input",
        )

    with col_send:
        send = st.button(
            "Ask →",
            use_container_width=True,
            key="chat_send",
        )

    if send and question.strip():
        _handle_question(
            user_id=user_id,
            question=question.strip(),
            simulation_context=simulation_context,
        )


def _handle_question(
    user_id: str,
    question: str,
    simulation_context: dict = None,
) -> None:
    """Process a question through the RAG engine."""

    # ── Always guarantee list before any append ───────────────────────────────
    _ensure_chat_list()

    # Add user message immediately
    st.session_state.chat_messages.append({
        "role":    "user",
        "content": question,
        "sources": [],
    })

    # Get AI response
    with st.spinner("GenEV AI is thinking..."):
        engine = get_rag_engine()
        result = engine.ask(
            user_id=user_id,
            question=question,
            simulation_context=simulation_context,
        )

    answer  = result.get("answer", "Sorry, I could not generate a response.")
    sources = result.get("sources", [])

    # Add assistant message
    st.session_state.chat_messages.append({
        "role":    "assistant",
        "content": answer,
        "sources": sources,
    })

    # Clear input field
    if "chat_input" in st.session_state:
        st.session_state.chat_input = ""

    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Suggested questions
# ─────────────────────────────────────────────────────────────────────────────

def _render_suggested_questions(simulation_context: dict = None) -> None:
    """Render clickable suggested question chips."""
    st.markdown(
        "<p style='font-size:12px;color:#94A3B8;margin-top:12px;'>"
        "💡 Suggested questions</p>",
        unsafe_allow_html=True,
    )

    if simulation_context:
        params  = simulation_context.get("params", {})
        metrics = simulation_context.get("metrics", {})
        thermal = metrics.get("thermal_risk_pct", 0)
        style   = params.get("driving_style", "moderate")
        terrain = params.get("terrain", "urban")

        suggestions = [
            f"Why was thermal risk {'high' if thermal > 50 else 'low'} "
            f"in my simulation?",
            f"How does {style} driving affect battery life?",
            f"What EV is best for {terrain} terrain in India?",
            "How can I improve my efficiency score?",
            "What is the best charging strategy for my scenario?",
        ]
    else:
        suggestions = [
            "Best EV for daily commute in Delhi?",
            "How does fast charging affect battery life?",
            "Real-world range of Tata Nexon EV?",
            "Home charging cost per km in India?",
            "What EV subsidies are available in India?",
        ]

    cols = st.columns(3)
    for idx, (col, suggestion) in enumerate(zip(cols, suggestions[:3])):
        with col:
            label = (
                suggestion[:45] + "..."
                if len(suggestion) > 45
                else suggestion
            )
            if st.button(
                label,
                key=f"suggest_{idx}",
                use_container_width=True,
                help=suggestion,
            ):
                _handle_question(
                    user_id=get_user_id(),
                    question=suggestion,
                    simulation_context=simulation_context,
                )