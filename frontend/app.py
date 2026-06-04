"""
frontend/app.py — Main GenEV 2.0 Streamlit application.

Tabs
----
1. 🧪 Simulator   — prompt input, run simulation, view results
2. 🤖 AI Chat     — RAG-powered conversational AI
3. 📜 History     — personal simulation history
4. 🔀 Comparison  — side-by-side multi-run analysis
5. 💎 Premium     — subscription and pricing
6. ℹ️  About       — platform info, feedback, creator

Run with:
    streamlit run frontend/app.py
"""

import time
import sys
import os

# ── Path fix ──────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st

from config import APP_TITLE, APP_VERSION
from auth.auth_handler import (
    is_logged_in,
    restore_session,
    get_user_id,
    get_user_name,
    get_profile_cached,
    refresh_profile,
    is_premium,
    sign_out,
)
from auth.auth_ui import render_auth_page, render_user_sidebar
from database.supabase_client import (
    save_simulation_run,
    get_all_simulation_runs,
    get_simulation_run_by_id,
    get_runs_for_comparison,
    delete_simulation_run,
    check_simulation_limit,
    increment_simulation_count,
)
from simulation_engine.scenario_parser import parse_scenario
from simulation_engine.simulator import (
    run_simulation,
    _compute_summary,
    _build_scenario_label,
    _enrich_telemetry,
)
from simulation_engine.metrics import compute_metrics
from ai_insights.insight_engine import generate_insights
from export.pdf_exporter import generate_pdf
from frontend.components.charts import (
    battery_chart,
    thermal_chart,
    speed_chart,
    voltage_chart,
    regen_chart,
    power_chart,
    radar_chart,
)
from frontend.components.metrics_panel import (
    render_metric_cards,
    render_grade_badges,
    render_risk_flags,
    render_overall_score,
    render_summary_stats,
    render_ai_gain_banner,
)
from frontend.components.ai_chat import render_ai_chat
from frontend.components.subscription import render_subscription_page
from frontend.components.about import render_about_page


# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title=f"{APP_TITLE} — EV Intelligence Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────────────────────────────────────────
# Global CSS
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .stButton > button {
        background: linear-gradient(135deg, #1D9E75, #15795A) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 8px 24px !important;
        transition: opacity 0.2s !important;
    }
    .stButton > button:hover { opacity: 0.88 !important; }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px; border-radius: 10px; padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px; padding: 6px 18px; font-size: 13px;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(29,158,117,0.15) !important;
        color: #1D9E75 !important;
        font-weight: 600;
    }
    .stTextArea textarea {
        border: 1.5px solid #CBD5E1 !important;
        border-radius: 10px !important;
        font-size: 14px !important;
    }
    .stTextArea textarea:focus {
        border-color: #1D9E75 !important;
        box-shadow: 0 0 0 2px rgba(29,158,117,0.20) !important;
    }
    .stMultiSelect [data-baseweb="tag"] {
        background: rgba(29,158,117,0.20) !important;
        color: #1D9E75 !important;
    }
    .stSpinner > div { border-top-color: #1D9E75 !important; }
    .stAlert { border-radius: 10px !important; }
    [data-testid="stSidebar"] {
        border-right: 1px solid #E2E8F0 !important;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Session state defaults
# ─────────────────────────────────────────────────────────────────────────────

def _init_session_state():
    defaults = {
        "last_result":   None,
        "last_metrics":  None,
        "last_run_id":   None,
        "preset_prompt": "",
        "prompt_input":  "",
        "chat_messages": [],    # ← always a list, never None
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # Fix: if chat_messages exists but is None, reset to list
    if not isinstance(st.session_state.get("chat_messages"), list):
        st.session_state.chat_messages = []

_init_session_state()


# ─────────────────────────────────────────────────────────────────────────────
# Auth gate
# ─────────────────────────────────────────────────────────────────────────────

def _check_auth() -> bool:
    if is_logged_in():
        return True
    if restore_session():
        return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────

def _render_sidebar():
    with st.sidebar:
        st.markdown(
            f'<div style="text-align:center;padding:16px 0 8px;">'
            f'<div style="font-size:32px;">⚡</div>'
            f'<div style="font-size:22px;font-weight:700;color:#1D9E75;">'
            f'{APP_TITLE}</div>'
            f'<div style="font-size:11px;color:#64748B;margin-top:2px;">'
            f'v{APP_VERSION} · EV Intelligence Platform</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.divider()
        render_user_sidebar()
        st.divider()

        # Quick presets
        st.markdown("**⚡ Quick Presets**")
        presets = {
            "🌡️ Delhi Summer":    "Simulate an EV driving in extreme Delhi summer traffic with repeated fast charging.",
            "❄️ Cold + Hilly":    "Simulate cold-weather EV driving on hilly terrain with aggressive acceleration.",
            "🛣️ Highway Eco":     "Simulate EV on a long highway cruise with eco driving and slow charging.",
            "🌧️ Monsoon Traffic": "Simulate EV in heavy monsoon rain with stop-and-go city traffic.",
            "🏔️ Mountain Drive":  "Simulate EV on mountainous terrain with aggressive driving and no charging.",
            "🌙 Night Urban":     "Simulate EV in moderate urban traffic at night with mild temperatures.",
        }

        for label, prompt in presets.items():
            if st.button(label, use_container_width=True, key=f"preset_{label}"):
                st.session_state["preset_prompt"] = prompt
                st.session_state["prompt_input"]  = prompt

        st.divider()

        # Recent runs
        st.markdown("**📜 Recent Runs**")
        user_id = get_user_id()
        if user_id:
            try:
                history = get_all_simulation_runs(user_id, limit=6)
                if not history:
                    st.caption("No runs yet.")
                else:
                    for run in history:
                        m       = run.get("metrics", {})
                        overall = m.get("overall_score", 0)
                        color   = (
                            "#1D9E75" if overall >= 70 else
                            "#D97706" if overall >= 45 else
                            "#DC2626"
                        )
                        st.markdown(
                            f'<div style="border-left:3px solid {color};'
                            f'padding:6px 10px;margin-bottom:6px;'
                            f'border-radius:4px;background:rgba(0,0,0,0.02);">'
                            f'<div style="font-size:11px;color:{color};'
                            f'font-weight:600;">{overall:.0f}/100</div>'
                            f'<div style="font-size:11px;color:#64748B;'
                            f'white-space:nowrap;overflow:hidden;'
                            f'text-overflow:ellipsis;max-width:180px;">'
                            f'{run["prompt"][:45]}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
            except Exception:
                st.caption("Could not load history.")

        st.divider()
        st.caption(f"Built by Pratham Ahuja · GenEV v{APP_VERSION}")


# ─────────────────────────────────────────────────────────────────────────────
# Tab 1 — Simulator
# ─────────────────────────────────────────────────────────────────────────────

def _render_simulator_tab():
    st.markdown("## 🧪 EV Scenario Simulator")
    st.markdown(
        "<p style='color:#64748B;font-size:13px;'>"
        "Describe any EV operating scenario in natural language. "
        "GenEV will parse it with Groq, generate synthetic telemetry, "
        "simulate physics, compute metrics, and generate AI insights.</p>",
        unsafe_allow_html=True,
    )

    user_id = get_user_id()

    # ── Always fetch fresh limit ──────────────────────────────────────────────
    sim_allowed, sim_used, sim_limit = check_simulation_limit(user_id)

    if not sim_allowed:
        st.warning(
            f"You've used all {sim_limit} simulations for today. "
            f"Upgrade to Premium for unlimited simulations, "
            f"or your limit resets tomorrow.",
            icon="⚠️",
        )

    # ── Prompt input ──────────────────────────────────────────────────────────
    prompt = st.text_area(
        label="Scenario Prompt",
        value=st.session_state["preset_prompt"],
        placeholder="e.g. Simulate an EV driving in extreme Delhi summer traffic with repeated fast charging.",
        height=90,
        label_visibility="collapsed",
        key="prompt_input",
    )

    col_btn, col_seed, col_spacer = st.columns([2, 1, 4])
    with col_btn:
        run_clicked = st.button(
            "▶ Run Simulation",
            use_container_width=True,
            disabled=not sim_allowed,
        )
    with col_seed:
        seed = st.number_input(
            "Seed", min_value=0, max_value=9999,
            value=42, step=1,
            help="Random seed for reproducibility",
        )

    # Usage counter
    if sim_limit < 999:
        color = "#DC2626" if sim_used >= sim_limit else "#64748B"
        st.markdown(
            f'<p style="font-size:12px;color:{color};font-weight:500;">'
            f'🧪 Simulations today: {sim_used}/{sim_limit}</p>',
            unsafe_allow_html=True,
        )

    # ── Run pipeline ──────────────────────────────────────────────────────────
    if run_clicked and sim_allowed:
        actual_prompt = st.session_state.get("prompt_input", "").strip()

        if not actual_prompt:
            st.warning("Please enter a scenario prompt first.", icon="⚠️")
            return

        t_start = time.time()

        with st.status("Running GenEV simulation pipeline...", expanded=True) as status:

            st.write("🔍 Step 1 — Parsing scenario with Groq...")
            params = parse_scenario(actual_prompt)
            st.write(f"✅ Extracted {len(params)} parameters")

            st.write("📡 Step 2 — Generating synthetic telemetry...")
            result = run_simulation(params, seed=int(seed))
            st.write(f"✅ Generated {len(result['telemetry'])} telemetry steps")

            st.write("📊 Step 3 — Computing evaluation metrics...")
            metrics = compute_metrics(result)
            st.write(f"✅ Overall score: {metrics['overall_score']:.1f}/100")

            st.write("🤖 Step 4 — Generating AI insights with Groq...")
            insights = generate_insights(result, metrics)
            st.write(f"✅ Generated {len(insights)} insights")

            st.write("💾 Step 5 — Saving to your workspace...")
            run_id = save_simulation_run(
                user_id=user_id,
                prompt=actual_prompt,
                params=params,
                metrics=metrics,
                insights=insights,
                telemetry=result["telemetry"],
                duration_sec=round(time.time() - t_start, 2),
            )
            st.write("✅ Saved to your personal workspace")

            st.write("📈 Step 6 — Updating usage count...")
            increment_simulation_count(user_id)
            refresh_profile()
            st.write("✅ Usage count updated")

            status.update(
                label=f"✅ Simulation complete in {time.time() - t_start:.2f}s",
                state="complete",
            )

        st.session_state["preset_prompt"] = ""
        result["insights"]             = insights
        st.session_state.last_result   = result
        st.session_state.last_metrics  = metrics
        st.session_state.last_run_id   = run_id
        st.rerun()

    # ── Results ───────────────────────────────────────────────────────────────
    if st.session_state.last_result is None:
        _render_empty_state()
        return

    result  = st.session_state.last_result
    metrics = st.session_state.last_metrics

    _render_extracted_params(result["params"])
    st.divider()
    _render_results(result, metrics)


def _render_empty_state():
    st.markdown(
        '<div style="text-align:center;padding:60px 20px;">'
        '<div style="font-size:48px;margin-bottom:16px;">⚡</div>'
        '<div style="font-size:18px;font-weight:600;color:#334155;'
        'margin-bottom:8px;">Ready to simulate</div>'
        '<div style="font-size:14px;color:#64748B;line-height:1.7;'
        'max-width:400px;margin:0 auto;">'
        'Enter a scenario prompt above or pick a preset from the sidebar. '
        'GenEV will generate realistic EV telemetry and AI-powered analysis.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _render_extracted_params(params: dict):
    with st.expander("🔍 Extracted Scenario Parameters", expanded=False):
        param_display = [
            ("🌡️ Temperature",   f"{params['temperature_c']}°C"),
            ("🗺️ Terrain",       params["terrain"].capitalize()),
            ("🚦 Traffic",       params["traffic"].replace("_", "-").capitalize()),
            ("🚗 Driving Style", params["driving_style"].capitalize()),
            ("🔌 Charging",      params["charging_mode"].replace("_", " ").capitalize()),
            ("🔁 Frequency",     params["charging_frequency"].capitalize()),
            ("🌦️ Weather",       params["weather"].capitalize()),
            ("🔋 Initial SoC",   f"{params['initial_battery_pct']:.0f}%"),
            ("📍 Distance",      f"{params['trip_distance_km']:.0f} km"),
            ("💧 Humidity",      f"{params['humidity_pct']:.0f}%"),
        ]
        cols = st.columns(5)
        for i, (label, value) in enumerate(param_display):
            with cols[i % 5]:
                st.markdown(
                    f'<div style="background:rgba(29,158,117,0.06);'
                    f'border:1px solid rgba(29,158,117,0.15);'
                    f'border-radius:8px;padding:10px 12px;'
                    f'margin-bottom:8px;text-align:center;">'
                    f'<div style="font-size:11px;color:#64748B;">{label}</div>'
                    f'<div style="font-size:13px;font-weight:600;'
                    f'color:#1E293B;margin-top:2px;">{value}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


def _render_results(result: dict, metrics: dict):
    render_overall_score(metrics, result["scenario_label"])
    render_grade_badges(metrics)
    render_ai_gain_banner(metrics)

    st.markdown("### 📊 Performance Metrics")
    render_metric_cards(metrics)
    render_risk_flags(metrics["risk_flags"])
    st.divider()

    st.markdown("### 📈 Telemetry Visualisation")
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(battery_chart(result["telemetry"]), use_container_width=True)
    with col2:
        st.plotly_chart(thermal_chart(result["telemetry"]), use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(speed_chart(result["telemetry"]), use_container_width=True)
    with col4:
        st.plotly_chart(voltage_chart(result["telemetry"]), use_container_width=True)

    col5, col6 = st.columns(2)
    with col5:
        st.plotly_chart(regen_chart(result["telemetry"]), use_container_width=True)
    with col6:
        st.plotly_chart(power_chart(result["telemetry"]), use_container_width=True)

    st.divider()
    col_radar, col_stats = st.columns([1, 1])
    with col_radar:
        st.plotly_chart(radar_chart(metrics), use_container_width=True)
    with col_stats:
        render_summary_stats(result["summary"])

    st.divider()
    st.markdown("### 🤖 AI Insights")
    for i, insight in enumerate(result.get("insights", []), 1):
        st.markdown(
            f'<div style="background:rgba(29,158,117,0.05);'
            f'border-left:3px solid #1D9E75;border-radius:6px;'
            f'padding:12px 16px;margin-bottom:10px;font-size:14px;'
            f'color:#1E293B;line-height:1.7;">'
            f'<span style="color:#1D9E75;font-weight:600;">{i}.</span> '
            f'{insight}</div>',
            unsafe_allow_html=True,
        )

    st.divider()
    _render_pdf_export(result, metrics)


def _render_pdf_export(result: dict, metrics: dict):
    st.markdown("### 📄 Export Report")

    if not is_premium():
        st.markdown(
            '<div style="background:#FEF3C7;border:1px solid #D97706;'
            'border-radius:10px;padding:12px 16px;font-size:13px;color:#1E293B;">'
            '🔒 <strong>PDF Export</strong> is a Premium feature. '
            'Upgrade to download branded simulation reports.'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    if st.button("📄 Download PDF Report", key="pdf_export_btn"):
        with st.spinner("Generating PDF report..."):
            try:
                pdf_bytes = generate_pdf(
                    simulation_result=result,
                    metrics=metrics,
                    insights=result.get("insights", []),
                    user_name=get_user_name(),
                    prompt=st.session_state.get("prompt_input", ""),
                )
                st.download_button(
                    label="⬇️ Click to Download PDF",
                    data=pdf_bytes,
                    file_name=f"genev_report_{result['scenario_label'][:30].replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    key="pdf_download_btn",
                )
            except Exception as e:
                st.error(f"PDF generation failed: {e}", icon="🔴")


# ─────────────────────────────────────────────────────────────────────────────
# Tab 3 — History
# ─────────────────────────────────────────────────────────────────────────────

def _render_history_tab():
    st.markdown("## 📜 My Simulation History")
    st.markdown(
        "<p style='color:#64748B;font-size:13px;'>"
        "Your personal simulation runs — only visible to you.</p>",
        unsafe_allow_html=True,
    )

    user_id = get_user_id()
    if not user_id:
        return

    try:
        history = get_all_simulation_runs(user_id, limit=50)
    except Exception as e:
        st.error(f"Could not load history: {e}", icon="🔴")
        return

    if not history:
        st.info("No simulations saved yet. Run your first scenario!", icon="ℹ️")
        return

    st.markdown(f"**{len(history)} runs saved**")

    for run in history:
        m       = run.get("metrics", {})
        overall = m.get("overall_score", 0)
        color   = (
            "#1D9E75" if overall >= 70 else
            "#D97706" if overall >= 45 else
            "#DC2626"
        )
        created = run.get("created_at", "")[:16].replace("T", " ")

        with st.expander(
            f"#{run['id'][:8]}... — {run['prompt'][:65]}"
            f"{'...' if len(run['prompt']) > 65 else ''}",
            expanded=False,
        ):
            col_info, col_metrics, col_actions = st.columns([3, 3, 1])

            with col_info:
                st.markdown(
                    f'<div style="font-size:12px;color:#64748B;margin-bottom:6px;">'
                    f'🕐 {created} UTC</div>'
                    f'<div style="font-size:13px;color:#1E293B;line-height:1.6;">'
                    f'{run["prompt"]}</div>',
                    unsafe_allow_html=True,
                )

            with col_metrics:
                mini = [
                    ("Overall",    overall,                           True),
                    ("Efficiency", m.get("efficiency_score", 0),     True),
                    ("Stress",     m.get("battery_stress_index", 0), False),
                    ("Thermal",    m.get("thermal_risk_pct", 0),     False),
                ]
                for label, val, hib in mini:
                    c = (
                        "#1D9E75" if (val >= 70 if hib else val <= 30) else
                        "#D97706" if (val >= 45 if hib else val <= 60) else
                        "#DC2626"
                    )
                    st.markdown(
                        f'<div style="display:flex;justify-content:space-between;'
                        f'padding:4px 0;font-size:12px;'
                        f'border-bottom:1px solid #F1F5F9;">'
                        f'<span style="color:#64748B;">{label}</span>'
                        f'<span style="color:{c};font-weight:600;">{val:.1f}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            with col_actions:
                if st.button("📂 Load", key=f"load_{run['id']}",
                             use_container_width=True):
                    full = get_simulation_run_by_id(run["id"], user_id)
                    if full:
                        enriched = _enrich_telemetry(
                            full["telemetry"], full["params"]
                        )
                        reconstructed = {
                            "telemetry":      enriched,
                            "summary":        _compute_summary(enriched, full["params"]),
                            "params":         full["params"],
                            "scenario_label": _build_scenario_label(full["params"]),
                            "insights":       full["insights"],
                        }
                        st.session_state.last_result  = reconstructed
                        st.session_state.last_metrics = full["metrics"]
                        st.session_state.last_run_id  = full["id"]
                        st.success("Loaded!", icon="✅")
                        st.rerun()

                if st.button("🗑️ Delete", key=f"del_{run['id']}",
                             use_container_width=True):
                    delete_simulation_run(run["id"], user_id)
                    if st.session_state.last_run_id == run["id"]:
                        st.session_state.last_result  = None
                        st.session_state.last_metrics = None
                        st.session_state.last_run_id  = None
                    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Tab 4 — Comparison
# ─────────────────────────────────────────────────────────────────────────────

def _render_comparison_tab():
    user_id = get_user_id()
    if not user_id:
        return

    st.markdown("### 🔀 Scenario Comparison")
    st.markdown(
        "Compare up to **4 of your past runs** side-by-side. "
        "Deltas shown relative to the first selected run."
    )

    try:
        all_runs = get_all_simulation_runs(user_id, limit=50)
    except Exception as e:
        st.error(f"Could not load runs: {e}", icon="🔴")
        return

    if len(all_runs) < 2:
        st.info("Run at least **2 simulations** to enable comparison.", icon="ℹ️")
        return

    run_options = {
        f"{run['prompt'][:55]}{'...' if len(run['prompt']) > 55 else ''} "
        f"[{run.get('created_at','')[:10]}]": run["id"]
        for run in all_runs
    }

    selected_labels = st.multiselect(
        "Select runs to compare",
        options=list(run_options.keys()),
        default=list(run_options.keys())[:2],
        max_selections=4,
    )

    if len(selected_labels) < 2:
        st.warning("Please select at least 2 runs.", icon="⚠️")
        return

    selected_ids = [run_options[lbl] for lbl in selected_labels]
    runs = get_runs_for_comparison(selected_ids, user_id)

    if len(runs) < 2:
        st.error("Could not load run data.", icon="🔴")
        return

    for run in runs:
        if run.get("telemetry") and "power_kw" not in run["telemetry"][0]:
            run["telemetry"] = _enrich_telemetry(
                run["telemetry"], run["params"]
            )

    from frontend.components.comparison import (
        _render_scenario_labels,
        _render_metric_diff_table,
        _render_comparison_charts,
        _render_telemetry_overlay,
        _render_winner_summary,
    )

    _render_scenario_labels(runs)
    st.divider()
    _render_metric_diff_table(runs)
    st.divider()
    _render_comparison_charts(runs)
    st.divider()
    _render_telemetry_overlay(runs)
    st.divider()
    _render_winner_summary(runs)


# ─────────────────────────────────────────────────────────────────────────────
# Main layout
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # ── Auth gate ─────────────────────────────────────────────────────────────
    if not _check_auth():
        render_auth_page()
        return

    # ── Authenticated layout ──────────────────────────────────────────────────
    _render_sidebar()

    # Build simulation context for AI chat
    sim_context = None
    if st.session_state.last_result and st.session_state.last_metrics:
        sim_context = {
            **st.session_state.last_result,
            "metrics": st.session_state.last_metrics,
        }

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🧪 Simulator",
        "🤖 AI Chat",
        "📜 History",
        "🔀 Comparison",
        "💎 Premium",
        "ℹ️ About",
    ])

    with tab1:
        _render_simulator_tab()

    with tab2:
        render_ai_chat(simulation_context=sim_context)

    with tab3:
        _render_history_tab()

    with tab4:
        _render_comparison_tab()

    with tab5:
        render_subscription_page()

    with tab6:
        render_about_page()

    st.markdown(
        f'<div style="text-align:center;padding:16px;'
        f'border-top:1px solid #E2E8F0;margin-top:20px;">'
        f'<span style="font-size:11px;color:#94A3B8;">'
        f'Built by <strong style="color:#1D9E75;">Pratham Ahuja</strong> · '
        f'GenEV v{APP_VERSION} · AI-Powered EV Intelligence'
        f'</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()