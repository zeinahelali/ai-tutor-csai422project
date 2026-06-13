"""
agents/graph.py
LangGraph multi-agent graph for the AI Tutor.

Graph structure:
  [START] → supervisor → guardrail_check → {curriculum | explainer | quiz | feedback | END}
                                                         ↓
                                                      [END]
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langgraph.graph import StateGraph, END
from state import TutorState
from agents.nodes import (
    supervisor_node,
    guardrail_node,
    curriculum_planner_node,
    explainer_node,
    quiz_node,
    feedback_synthesizer_node,
)


# ── Routing function (called after guardrail_node) ────────────────────────────

def route_after_guardrail(state: TutorState) -> str:
    """
    If guardrail blocked the response, go to END.
    Otherwise route to the agent identified by supervisor.
    """
    if state.get("next_agent") == "END":
        return END

    return state.get("next_agent", "explainer")


# ── Build the graph ───────────────────────────────────────────────────────────

def build_tutor_graph() -> StateGraph:
    workflow = StateGraph(TutorState)

    # Add all nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("guardrail", guardrail_node)
    workflow.add_node("curriculum", curriculum_planner_node)
    workflow.add_node("explainer", explainer_node)
    workflow.add_node("quiz", quiz_node)
    workflow.add_node("feedback", feedback_synthesizer_node)

    # Entry point
    workflow.set_entry_point("supervisor")

    # Supervisor → guardrail (always)
    workflow.add_edge("supervisor", "guardrail")

    # Guardrail → conditional routing
    workflow.add_conditional_edges(
        "guardrail",
        route_after_guardrail,
        {
            "curriculum": "curriculum",
            "explainer": "explainer",
            "quiz": "quiz",
            "feedback": "feedback",
            END: END,
        },
    )

    # All agent nodes → END
    workflow.add_edge("curriculum", END)
    workflow.add_edge("explainer", END)
    workflow.add_edge("quiz", END)
    workflow.add_edge("feedback", END)

    return workflow.compile()


# ── Singleton accessor ────────────────────────────────────────────────────────

_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_tutor_graph()
    return _graph
