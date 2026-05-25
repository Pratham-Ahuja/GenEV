"""
rag/rag_engine.py

RAG (Retrieval Augmented Generation) engine for GenEV 2.0.

Flow
----
1. Accept user question + simulation context
2. Retrieve relevant chunks from ChromaDB
3. Build contextual prompt with simulation data
4. Call Groq LLaMA for grounded response
5. Save Q&A to Supabase chat history
6. Return answer + sources

Classes
-------
RAGEngine — main engine class, instantiated once per session
"""

import json
from groq import Groq

from config import GROQ_API_KEY, GROQ_MODEL
from rag.embeddings import get_or_build_index, retrieve
from database.supabase_client import (
    save_chat_message,
    check_question_limit,
    increment_question_count,
)


# ─────────────────────────────────────────────────────────────────────────────
# System prompt
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """
You are GenEV AI — an expert electric vehicle intelligence assistant
built into the GenEV simulation platform.

You have access to:
1. A knowledge base of Indian EV specifications, battery science,
   charging guides, and EV ownership insights
2. The user's most recent simulation results and metrics

Your job is to answer the user's question by combining:
- Retrieved knowledge base context (provided below)
- The user's simulation context (provided below)
- Your own EV expertise

Rules:
- Always be specific and data-driven
- Reference actual numbers from simulation context when relevant
- Reference specific EV models, specs, and Indian market data
- Keep answers concise — 3-5 sentences for simple questions
- Use bullet points for complex multi-part answers
- Never make up EV specifications — use only provided knowledge
- If question is unrelated to EVs, politely redirect to EV topics
- Always end with one actionable recommendation when possible
- Write in a friendly, expert tone suitable for Indian EV buyers
""".strip()


# ─────────────────────────────────────────────────────────────────────────────
# RAG Engine
# ─────────────────────────────────────────────────────────────────────────────

class RAGEngine:
    """
    Main RAG engine for GenEV conversational AI.

    Usage
    -----
    engine = RAGEngine()
    result = engine.ask(
        user_id="uuid",
        question="Why was thermal risk high?",
        simulation_context={...}  # from last simulation
    )
    """

    def __init__(self):
        self._client     = Groq(api_key=GROQ_API_KEY)
        self._collection = None
        self._load_index()

    def _load_index(self):
        """Load or build the ChromaDB index on initialization."""
        try:
            self._collection = get_or_build_index()
            print(f"[rag_engine] Knowledge base ready: "
                  f"{self._collection.count()} chunks")
        except Exception as e:
            print(f"[rag_engine] Warning: Could not load index: {e}")
            self._collection = None

    # ─────────────────────────────────────────────────────────────────────────
    # Main ask method
    # ─────────────────────────────────────────────────────────────────────────

    def ask(
        self,
        user_id: str,
        question: str,
        simulation_context: dict = None,
    ) -> dict:
        """
        Answer a question using RAG + simulation context.

        Parameters
        ----------
        user_id             : Supabase user UUID
        question            : user's question string
        simulation_context  : dict from last simulation run (optional)

        Returns
        -------
        dict with keys:
            answer   : str  — AI response
            sources  : list — knowledge base sources used
            allowed  : bool — whether question was allowed (limit check)
            used     : int  — questions used today
            limit    : int  — daily question limit
        """

        # ── Check question limit ──────────────────────────────────────────────
        allowed, used, limit = check_question_limit(user_id)

        if not allowed:
            return {
                "answer":  (
                    f"You have used all {limit} AI questions for today. "
                    f"Upgrade to GenEV Premium for {10} questions/day, "
                    f"or your limit resets tomorrow."
                ),
                "sources": [],
                "allowed": False,
                "used":    used,
                "limit":   limit,
            }

        # ── Retrieve relevant knowledge ───────────────────────────────────────
        sources     = []
        context_str = ""

        if self._collection is not None:
            try:
                chunks = retrieve(
                    query=question,
                    top_k=4,
                    collection=self._collection,
                )
                if chunks:
                    context_str = self._format_retrieved_context(chunks)
                    sources     = list({c["source"] for c in chunks})
            except Exception as e:
                print(f"[rag_engine] Retrieval error: {e}")

        # ── Build simulation context string ───────────────────────────────────
        sim_str = self._format_simulation_context(simulation_context)

        # ── Build full prompt ─────────────────────────────────────────────────
        user_message = self._build_user_message(
            question=question,
            retrieved_context=context_str,
            simulation_context=sim_str,
        )

        # ── Call Groq ─────────────────────────────────────────────────────────
        try:
            answer = self._call_groq(user_message)
        except Exception as e:
            print(f"[rag_engine] Groq call failed: {e}")
            answer = self._fallback_answer(question, simulation_context)

        # ── Save to chat history ──────────────────────────────────────────────
        try:
            save_chat_message(
                user_id=user_id,
                question=question,
                answer=answer,
                sources=sources,
                simulation_context=simulation_context or {},
            )
        except Exception as e:
            print(f"[rag_engine] Failed to save chat: {e}")

        # ── Increment question count ──────────────────────────────────────────
        try:
            increment_question_count(user_id)
            used += 1
        except Exception as e:
            print(f"[rag_engine] Failed to increment count: {e}")

        return {
            "answer":  answer,
            "sources": sources,
            "allowed": True,
            "used":    used,
            "limit":   limit,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Context formatters
    # ─────────────────────────────────────────────────────────────────────────

    def _format_retrieved_context(self, chunks: list[dict]) -> str:
        """Format retrieved knowledge chunks into a readable context string."""
        if not chunks:
            return ""

        parts = ["RETRIEVED KNOWLEDGE BASE CONTEXT:"]
        for i, chunk in enumerate(chunks, 1):
            source = chunk["source"].replace("_", " ").title()
            score  = chunk["score"]
            parts.append(
                f"\n[Source {i}: {source} | Relevance: {score:.2f}]\n"
                f"{chunk['text'][:600]}"
            )

        return "\n".join(parts)

    def _format_simulation_context(
        self,
        simulation_context: dict = None,
    ) -> str:
        """Format simulation results into a concise context string."""
        if not simulation_context:
            return "No simulation context available."

        params  = simulation_context.get("params", {})
        metrics = simulation_context.get("metrics", {})
        summary = simulation_context.get("summary", {})
        label   = simulation_context.get("scenario_label", "Unknown scenario")

        lines = [
            "USER'S SIMULATION CONTEXT:",
            f"Scenario: {label}",
            "",
            "Operating Conditions:",
            f"  Temperature: {params.get('temperature_c', 'N/A')}°C",
            f"  Terrain: {params.get('terrain', 'N/A')}",
            f"  Traffic: {params.get('traffic', 'N/A')}",
            f"  Driving style: {params.get('driving_style', 'N/A')}",
            f"  Charging mode: {params.get('charging_mode', 'N/A')}",
            f"  Weather: {params.get('weather', 'N/A')}",
            "",
            "Performance Metrics:",
            f"  Overall score: {metrics.get('overall_score', 'N/A')}/100",
            f"  Efficiency score: {metrics.get('efficiency_score', 'N/A')}/100",
            f"  Battery stress index: {metrics.get('battery_stress_index', 'N/A')}/100",
            f"  Thermal risk: {metrics.get('thermal_risk_pct', 'N/A')}%",
            f"  Stability score: {metrics.get('stability_score', 'N/A')}/100",
            f"  Charging efficiency: {metrics.get('charging_efficiency', 'N/A')}%",
            f"  AI optimisation gain: {metrics.get('ai_optimization_gain', 'N/A')}%",
            "",
            "Trip Summary:",
            f"  Total distance: {summary.get('total_distance_km', 'N/A')} km",
            f"  Energy consumed: {summary.get('total_energy_kwh', 'N/A')} kWh",
            f"  Average speed: {summary.get('avg_speed_kmh', 'N/A')} km/h",
            f"  Peak temperature: {summary.get('max_temp_c', 'N/A')}°C",
            f"  Final battery: {summary.get('final_battery_pct', 'N/A')}%",
            f"  Thermal warnings: {summary.get('thermal_violations', 'N/A')}",
            f"  Regen recovery: {summary.get('regen_recovery_pct', 'N/A')}%",
        ]

        return "\n".join(lines)

    def _build_user_message(
        self,
        question: str,
        retrieved_context: str,
        simulation_context: str,
    ) -> str:
        """Build the complete user message for Groq."""
        parts = []

        if retrieved_context:
            parts.append(retrieved_context)

        if simulation_context:
            parts.append("\n" + simulation_context)

        parts.append(f"\nUSER QUESTION: {question}")
        parts.append(
            "\nPlease answer the question using the context above. "
            "Be specific, reference actual numbers where relevant, "
            "and end with one actionable recommendation."
        )

        return "\n".join(parts)

    # ─────────────────────────────────────────────────────────────────────────
    # Groq call
    # ─────────────────────────────────────────────────────────────────────────

    def _call_groq(self, user_message: str) -> str:
        """Call Groq LLaMA and return the response text."""
        response = self._client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system",  "content": _SYSTEM_PROMPT},
                {"role": "user",    "content": user_message},
            ],
            temperature=0.4,
            max_tokens=800,
        )
        return response.choices[0].message.content.strip()

    # ─────────────────────────────────────────────────────────────────────────
    # Fallback answer
    # ─────────────────────────────────────────────────────────────────────────

    def _fallback_answer(
        self,
        question: str,
        simulation_context: dict = None,
    ) -> str:
        """
        Rule-based fallback answer when Groq is unavailable.
        Uses simulation context to give a basic response.
        """
        q = question.lower()

        if simulation_context:
            metrics = simulation_context.get("metrics", {})
            params  = simulation_context.get("params", {})

            thermal = metrics.get("thermal_risk_pct", 0)
            stress  = metrics.get("battery_stress_index", 0)
            eff     = metrics.get("efficiency_score", 0)
            temp    = params.get("temperature_c", 25)

            if any(w in q for w in ["thermal", "heat", "temperature", "hot"]):
                return (
                    f"Your simulation showed a thermal risk of {thermal:.1f}% "
                    f"with peak temperature reaching {simulation_context.get('summary', {}).get('max_temp_c', 'N/A')}°C. "
                    f"At {temp}°C ambient temperature, battery cooling systems "
                    f"work harder, accelerating heat buildup. "
                    f"Recommendation: Space out charging sessions by at least "
                    f"30 minutes to allow battery cooling between charges."
                )

            if any(w in q for w in ["stress", "battery", "degradation"]):
                return (
                    f"Your battery stress index is {stress:.1f}/100. "
                    f"Key contributors: {params.get('charging_mode', 'fast')} charging "
                    f"and {params.get('driving_style', 'moderate')} driving style. "
                    f"Recommendation: Switch to AC charging for daily use and "
                    f"limit DC fast charging to long trips only."
                )

            if any(w in q for w in ["efficiency", "range", "energy"]):
                return (
                    f"Your efficiency score is {eff:.1f}/100. "
                    f"The {params.get('terrain', 'urban')} terrain and "
                    f"{params.get('traffic', 'moderate')} traffic conditions "
                    f"are the primary factors affecting energy consumption. "
                    f"Recommendation: Use Eco driving mode in heavy traffic "
                    f"to improve efficiency by 10-15%."
                )

        return (
            "I'm having trouble connecting to the AI service right now. "
            "Please try again in a moment. In the meantime, check the "
            "simulation metrics panel for detailed analysis of your scenario."
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Conversation history builder
    # ─────────────────────────────────────────────────────────────────────────

    def build_context_from_history(
        self,
        chat_history: list[dict],
        simulation_context: dict = None,
    ) -> str:
        """
        Build a conversation summary from recent chat history.
        Used to give the AI memory of recent questions in the session.
        """
        if not chat_history:
            return ""

        lines = ["RECENT CONVERSATION HISTORY:"]
        for msg in chat_history[-4:]:  # last 4 exchanges
            lines.append(f"User: {msg.get('question', '')}")
            answer = msg.get("answer", "")
            lines.append(f"GenEV AI: {answer[:200]}...")
            lines.append("")

        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton
# ─────────────────────────────────────────────────────────────────────────────

_engine_instance: RAGEngine = None


def get_rag_engine() -> RAGEngine:
    """
    Get or create the RAG engine singleton.
    Use this in Streamlit to avoid rebuilding on every rerun.
    """
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = RAGEngine()
    return _engine_instance