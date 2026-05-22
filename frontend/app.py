"""
frontend/app.py — Main GenEV Streamlit application.

Tabs
----
1. 🧪 Simulator   — prompt input, run simulation, view results
2. 📜 History     — browse and reload past runs
3. 🔀 Comparison  — side-by-side multi-run analysis
4. ℹ️  About       — project info and tech stack

Run with:
    streamlit run frontend/app.py
"""

import time
import sys
import os

# ── Path fix so imports work from any working directory ───────────────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st

from config import APP_TITLE, APP_VERSION
from database.db import init_db, get_all_runs, get_run_by_id, delete_run
from simulation_engine.scenario_parser import parse_scenario
from simulation_engine.simulator import run_simulation
from simulation_engine.metrics import compute_metrics
from ai_insights.insight_engine import generate_insights
from database.db import save_run

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
from frontend.components.comparison import render_comparison_panel


# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title=f"{APP_TITLE} — EV Scenario Simulator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────────────────────────────────────────
# Global CSS
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    /* Base */
    .stApp { background-color: #0F1117; }

    /* Hide default Streamlit header */
    header[data-testid="stHeader"] { background: transparent; }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(255,255,255,0.03);
        border-radius: 10px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 6px 18px;
        font-size: 13px;
        color: #94A3B8;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(29,158,117,0.15) !important;
        color: #1D9E75 !important;
        font-weight: 600;
    }

    /* Input */
    .stTextArea textarea {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
        border-radius: 10px !important;
        color: #E2E8F0 !important;
        font-size: 14px !important;
    }
    .stTextArea textarea:focus {
        border-color: #1D9E75 !important;
        box-shadow: 0 0 0 2px rgba(29,158,117,0.20) !important;
    }

    /* Buttons */
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

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: rgba(255,255,255,0.02) !important;
        border-right: 1px solid rgba(255,255,255,0.06) !important;
    }

    /* Divider */
    hr { border-color: rgba(255,255,255,0.06) !important; }

    /* Plotly chart background */
    .js-plotly-plot .plotly { background: transparent !important; }

    /* Multiselect */
    .stMultiSelect [data-baseweb="tag"] {
        background: rgba(29,158,117,0.20) !important;
        color: #1D9E75 !important;
    }

    /* Selectbox */
    .stSelectbox [data-baseweb="select"] {
        background: rgba(255,255,255,0.04) !important;
    }

    /* Spinner */
    .stSpinner > div { border-top-color: #1D9E75 !important; }

    /* Success / info / warning boxes */
    .stAlert { border-radius: 10px !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Initialise DB on first load
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource
def _init():
    init_db()
    return True

_init()


# ─────────────────────────────────────────────────────────────────────────────
# Session state defaults
# ─────────────────────────────────────────────────────────────────────────────

if "last_result"  not in st.session_state: st.session_state.last_result  = None
if "last_metrics" not in st.session_state: st.session_state.last_metrics = None
if "last_run_id"  not in st.session_state: st.session_state.last_run_id  = None
if "history"      not in st.session_state: st.session_state.history      = []


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────

def _render_sidebar():
    with st.sidebar:
        # Logo
        st.markdown(f"""
        <div style="text-align:center; padding: 20px 0 10px;">
            <div style="font-size:32px;">⚡</div>
            <div style="font-size:22px; font-weight:700;
                        color:#1D9E75; letter-spacing:0.05em;">
                {APP_TITLE}
            </div>
            <div style="font-size:11px; color:#64748B; margin-top:2px;">
                v{APP_VERSION} · EV Scenario Sandbox
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # Quick scenario presets
        st.markdown("**⚡ Quick Presets**")
        presets = {
            "🌡️ Delhi Summer":     "Simulate an EV driving in extreme Delhi summer traffic with repeated fast charging.",
            "❄️ Cold + Hilly":     "Simulate cold-weather EV driving on hilly terrain with aggressive acceleration.",
            "🛣️ Highway Eco":      "Simulate EV on a long highway cruise with eco driving and slow charging.",
            "🌧️ Monsoon Traffic":  "Simulate EV in heavy monsoon rain with stop-and-go city traffic.",
            "🏔️ Mountain Drive":   "Simulate EV on mountainous terrain with aggressive driving and no charging.",
            "🌙 Night Urban":      "Simulate EV in moderate urban traffic at night with mild temperatures.",
        }

        for label, prompt in presets.items():
            if st.button(label, use_container_width=True, key=f"preset_{label}"):
                st.session_state["preset_prompt"] = prompt
                st.rerun()

        st.divider()

        # Recent runs summary
        st.markdown("**📜 Recent Runs**")
        history = get_all_runs(limit=8)
        if not history:
            st.caption("No runs yet. Run your first simulation!")
        else:
            for run in history:
                m = run["metrics"]
                overall = m.get("overall_score", 0)
                color = (
                    "#1D9E75" if overall >= 70 else
                    "#D97706" if overall >= 45 else
                    "#DC2626"
                )
                st.markdown(f"""
                <div style="
                    border-left: 3px solid {color};
                    padding: 6px 10px;
                    margin-bottom: 6px;
                    border-radius: 4px;
                    background: rgba(255,255,255,0.02);
                ">
                    <div style="font-size:11px; color:{color}; font-weight:600;">
                        #{run['id']} · {overall:.0f}/100
                    </div>
                    <div style="font-size:11px; color:#64748B;
                                white-space:nowrap; overflow:hidden;
                                text-overflow:ellipsis; max-width:180px;">
                        {run['prompt'][:50]}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.divider()
        st.caption("Built with Streamlit · xAI Grok · Plotly")


# ─────────────────────────────────────────────────────────────────────────────
# Tab 1 — Simulator
# ─────────────────────────────────────────────────────────────────────────────

def _render_simulator_tab():
    st.markdown("## 🧪 EV Scenario Simulator")
    st.markdown(
        "Describe any EV operating scenario in natural language. "
        "GenEV will parse it with Grok, generate synthetic telemetry, "
        "simulate physics, compute metrics, and generate AI insights."
    )

    # ── Prompt input ──────────────────────────────────────────────────────────
    default_prompt = st.session_state.pop("preset_prompt", "")

    prompt = st.text_area(
        label="Scenario Prompt",
        value=default_prompt,
        placeholder="e.g. Simulate an EV driving in extreme Delhi summer traffic with repeated fast charging.",
        height=90,
        label_visibility="collapsed",
    )

    col_btn, col_seed, col_spacer = st.columns([2, 1, 4])
    with col_btn:
        run_clicked = st.button("▶ Run Simulation", use_container_width=True)
    with col_seed:
        seed = st.number_input(
            "Seed", min_value=0, max_value=9999,
            value=42, step=1,
            help="Random seed for reproducibility",
        )

    # ── Run pipeline ──────────────────────────────────────────────────────────
    if run_clicked:
        if not prompt.strip():
            st.warning("Please enter a scenario prompt first.", icon="⚠️")
            return

        t_start = time.time()

        with st.status("Running GenEV simulation pipeline...", expanded=True) as status:

            st.write("🔍 Step 1 — Parsing scenario with Grok...")
            params = parse_scenario(prompt)
            st.write(f"✅ Extracted {len(params)} parameters")

            st.write("📡 Step 2 — Generating synthetic telemetry...")
            result = run_simulation(params, seed=int(seed))
            st.write(f"✅ Generated {len(result['telemetry'])} telemetry steps")

            st.write("📊 Step 3 — Computing evaluation metrics...")
            metrics = compute_metrics(result)
            st.write(f"✅ Overall score: {metrics['overall_score']:.1f}/100")

            st.write("🤖 Step 4 — Generating AI insights with Grok...")
            insights = generate_insights(result, metrics)
            st.write(f"✅ Generated {len(insights)} insights")

            st.write("💾 Step 5 — Saving to database...")
            run_id = save_run(
                prompt=prompt,
                params=params,
                metrics=metrics,
                insights=insights,
                telemetry=result["telemetry"],
                duration_sec=round(time.time() - t_start, 2),
            )
            st.write(f"✅ Saved as Run #{run_id}")

            status.update(
                label=f"✅ Simulation complete in {time.time() - t_start:.2f}s",
                state="complete",
            )

        # Store in session
        result["insights"] = insights
        st.session_state.last_result  = result
        st.session_state.last_metrics = metrics
        st.session_state.last_run_id  = run_id
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
    st.markdown("""
    <div style="
        text-align:center;
        padding: 60px 20px;
        color:#64748B;
    ">
        <div style="font-size:48px; margin-bottom:16px;">⚡</div>
        <div style="font-size:18px; font-weight:600;
                    color:#94A3B8; margin-bottom:8px;">
            Ready to simulate
        </div>
        <div style="font-size:14px; line-height:1.7; max-width:400px; margin:0 auto;">
            Enter a scenario prompt above or pick a preset from the sidebar.
            GenEV will generate realistic EV telemetry and AI-powered analysis.
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_extracted_params(params: dict):
    """Show the LLM-extracted parameters in a collapsible section."""
    with st.expander("🔍 Extracted Scenario Parameters", expanded=False):
        cols = st.columns(5)
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
                st.markdown(f"""
                <div style="
                    background:rgba(255,255,255,0.03);
                    border-radius:8px;
                    padding:10px 12px;
                    margin-bottom:8px;
                    text-align:center;
                ">
                    <div style="font-size:11px; color:#64748B;">{label}</div>
                    <div style="font-size:14px; font-weight:600;
                                color:#E2E8F0; margin-top:2px;">{value}</div>
                </div>
                """, unsafe_allow_html=True)


def _render_results(result: dict, metrics: dict):
    """Render the full results dashboard."""

    # ── Overall score + grade badges ──────────────────────────────────────────
    render_overall_score(metrics, result["scenario_label"])
    render_grade_badges(metrics)
    render_ai_gain_banner(metrics)

    # ── Metric cards ──────────────────────────────────────────────────────────
    st.markdown("### 📊 Performance Metrics")
    render_metric_cards(metrics)

    # ── Risk flags ────────────────────────────────────────────────────────────
    render_risk_flags(metrics["risk_flags"])
    st.divider()

    # ── Charts row 1 — Battery + Thermal ─────────────────────────────────────
    st.markdown("### 📈 Telemetry Visualisation")
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(battery_chart(result["telemetry"]), use_container_width=True)
    with col2:
        st.plotly_chart(thermal_chart(result["telemetry"]), use_container_width=True)

    # ── Charts row 2 — Speed + Voltage ───────────────────────────────────────
    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(speed_chart(result["telemetry"]), use_container_width=True)
    with col4:
        st.plotly_chart(voltage_chart(result["telemetry"]), use_container_width=True)

    # ── Charts row 3 — Regen + Power ─────────────────────────────────────────
    col5, col6 = st.columns(2)
    with col5:
        st.plotly_chart(regen_chart(result["telemetry"]), use_container_width=True)
    with col6:
        st.plotly_chart(power_chart(result["telemetry"]), use_container_width=True)

    # ── Radar + Summary stats ─────────────────────────────────────────────────
    st.divider()
    col_radar, col_stats = st.columns([1, 1])
    with col_radar:
        st.plotly_chart(radar_chart(metrics), use_container_width=True)
    with col_stats:
        render_summary_stats(result["summary"])

    # ── AI Insights ───────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 🤖 AI Insights")
    insights = result.get("insights", [])
    for i, insight in enumerate(insights):
        st.markdown(f"""
        <div style="
            background: rgba(255,255,255,0.02);
            border-left: 3px solid #1D9E75;
            border-radius: 6px;
            padding: 12px 16px;
            margin-bottom: 10px;
            font-size: 14px;
            color: #CBD5E1;
            line-height: 1.7;
        ">
            <span style="color:#1D9E75; font-weight:600;">
                {i + 1}.
            </span>
            {insight}
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Tab 2 — History
# ─────────────────────────────────────────────────────────────────────────────

def _render_history_tab():
    st.markdown("## 📜 Simulation History")

    history = get_all_runs(limit=50)

    if not history:
        st.info("No simulations saved yet. Run your first scenario!", icon="ℹ️")
        return

    st.markdown(f"**{len(history)} runs saved**")

    for run in history:
        m       = run["metrics"]
        overall = m.get("overall_score", 0)
        color   = (
            "#1D9E75" if overall >= 70 else
            "#D97706" if overall >= 45 else
            "#DC2626"
        )
        created = run["created_at"][:16].replace("T", " ")

        with st.expander(
            f"#{run['id']} — {run['prompt'][:70]}{'...' if len(run['prompt']) > 70 else ''}",
            expanded=False,
        ):
            col_info, col_metrics, col_actions = st.columns([3, 3, 1])

            with col_info:
                st.markdown(f"""
                <div style="font-size:12px; color:#64748B; margin-bottom:6px;">
                    🕐 {created} UTC · Run #{run['id']}
                </div>
                <div style="font-size:13px; color:#CBD5E1; line-height:1.6;">
                    {run['prompt']}
                </div>
                """, unsafe_allow_html=True)

            with col_metrics:
                mini_metrics = [
                    ("Overall",    overall,                         True),
                    ("Efficiency", m.get("efficiency_score", 0),    True),
                    ("Stress",     m.get("battery_stress_index", 0),False),
                    ("Thermal",    m.get("thermal_risk_pct", 0),    False),
                ]
                for label, val, hib in mini_metrics:
                    c = (
                        "#1D9E75" if (val >= 70 if hib else val <= 30) else
                        "#D97706" if (val >= 45 if hib else val <= 60) else
                        "#DC2626"
                    )
                    st.markdown(f"""
                    <div style="display:flex; justify-content:space-between;
                                padding:4px 0; font-size:12px;
                                border-bottom:1px solid rgba(255,255,255,0.04);">
                        <span style="color:#94A3B8;">{label}</span>
                        <span style="color:{c}; font-weight:600;">{val:.1f}</span>
                    </div>
                    """, unsafe_allow_html=True)

            with col_actions:
                if st.button("📂 Load", key=f"load_{run['id']}",
                             use_container_width=True):
                    full = get_run_by_id(run["id"])
                    if full:
                        # Reconstruct result dict
                        reconstructed = {
                            "telemetry":      full["telemetry"],
                            "summary":        _recompute_summary(full["telemetry"], full["params"]),
                            "params":         full["params"],
                            "scenario_label": _build_label(full["params"]),
                            "insights":       full["insights"],
                        }
                        st.session_state.last_result  = reconstructed
                        st.session_state.last_metrics = full["metrics"]
                        st.session_state.last_run_id  = full["id"]
                        st.success(f"Run #{run['id']} loaded!", icon="✅")
                        st.rerun()

                if st.button("🗑️ Delete", key=f"del_{run['id']}",
                             use_container_width=True):
                    delete_run(run["id"])
                    if st.session_state.last_run_id == run["id"]:
                        st.session_state.last_result  = None
                        st.session_state.last_metrics = None
                        st.session_state.last_run_id  = None
                    st.rerun()


def _recompute_summary(telemetry: list, params: dict) -> dict:
    """Lightweight summary recompute for loaded runs (avoids re-running full sim)."""
    from simulation_engine.simulator import _compute_summary
    return _compute_summary(telemetry, params)


def _build_label(params: dict) -> str:
    from simulation_engine.simulator import _build_scenario_label
    return _build_scenario_label(params)


# ─────────────────────────────────────────────────────────────────────────────
# Tab 4 — About
# ─────────────────────────────────────────────────────────────────────────────

def _render_about_tab():
    st.markdown("## ℹ️ About GenEV")

    st.markdown("""
    <div style="
        background: rgba(29,158,117,0.08);
        border: 1px solid rgba(29,158,117,0.25);
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 20px;
    ">
        <div style="font-size:20px; font-weight:700; color:#1D9E75; margin-bottom:8px;">
            ⚡ GenEV — Generative AI EV Scenario Sandbox
        </div>
        <div style="font-size:14px; color:#CBD5E1; line-height:1.8;">
            GenEV is an AI-powered interactive platform that generates realistic EV
            operating scenarios from natural language prompts and simulates battery
            behaviour, thermal stress, charging efficiency, and operational risks in
            real time.
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🧠 How It Works")
        pipeline = [
            ("1", "Natural Language Prompt",    "You describe any EV scenario in plain English."),
            ("2", "LLM Scenario Parsing",       "Grok (xAI) extracts structured parameters."),
            ("3", "Synthetic Telemetry",        "NumPy generates realistic time-series data using EV physics."),
            ("4", "Simulation Engine",          "Physics-based computations model battery, thermal, and power behaviour."),
            ("5", "Metric Evaluation",          "6 metrics quantify efficiency, stress, risk, and stability."),
            ("6", "AI Insight Generation",      "Grok explains what happened and why, with recommendations."),
        ]
        for num, title, desc in pipeline:
            st.markdown(f"""
            <div style="
                display:flex; gap:14px; align-items:flex-start;
                margin-bottom:14px;
            ">
                <div style="
                    background:#1D9E75; color:white;
                    border-radius:50%; width:26px; height:26px;
                    display:flex; align-items:center; justify-content:center;
                    font-size:12px; font-weight:700; flex-shrink:0;
                ">
                    {num}
                </div>
                <div>
                    <div style="font-size:13px; font-weight:600;
                                color:#E2E8F0;">{title}</div>
                    <div style="font-size:12px; color:#94A3B8;
                                margin-top:2px; line-height:1.5;">{desc}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        st.markdown("### 🛠️ Tech Stack")
        stack = [
            ("🤖", "xAI Grok",      "LLM for scenario parsing and insight generation"),
            ("🌐", "Streamlit",     "Interactive web frontend"),
            ("📊", "Plotly",        "Interactive data visualisation"),
            ("🔢", "NumPy",         "Physics simulation and telemetry generation"),
            ("🗄️", "SQLite",        "Persistent run storage and history"),
            ("🐍", "Python",        "Core language — simulation engine and backend"),
        ]
        for icon, name, desc in stack:
            st.markdown(f"""
            <div style="
                background: rgba(255,255,255,0.03);
                border-radius: 8px;
                padding: 10px 14px;
                margin-bottom: 8px;
                display: flex;
                align-items: center;
                gap: 12px;
            ">
                <span style="font-size:20px;">{icon}</span>
                <div>
                    <div style="font-size:13px; font-weight:600;
                                color:#E2E8F0;">{name}</div>
                    <div style="font-size:11px; color:#64748B;">{desc}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("### 📊 Metrics Computed")
        metrics_list = [
            ("⚡", "Energy Efficiency Score",  "Distance / energy, normalised 0–100"),
            ("🔋", "Battery Stress Index",     "Thermal + charge + accel + discharge stress"),
            ("🌡️", "Thermal Risk Probability", "Likelihood of overheating event"),
            ("📊", "Stability Score",          "Voltage + thermal consistency"),
            ("🔌", "Charging Efficiency",      "Energy stored vs energy supplied"),
            ("🤖", "AI Optimisation Gain",     "Estimated improvement from AI recommendations"),
        ]
        for icon, name, formula in metrics_list:
            st.markdown(f"""
            <div style="
                padding: 7px 0;
                border-bottom: 1px solid rgba(255,255,255,0.04);
                font-size: 12px;
            ">
                <span style="color:#1D9E75;">{icon} {name}</span>
                <span style="color:#64748B; margin-left:8px;">— {formula}</span>
            </div>
            """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Main layout
# ─────────────────────────────────────────────────────────────────────────────

def main():
    _render_sidebar()

    tab1, tab2, tab3, tab4 = st.tabs([
        "🧪 Simulator",
        "📜 History",
        "🔀 Comparison",
        "ℹ️ About",
    ])

    with tab1:
        _render_simulator_tab()

    with tab2:
        _render_history_tab()

    with tab3:
        render_comparison_panel()

    with tab4:
        _render_about_tab()


if __name__ == "__main__":
    main()