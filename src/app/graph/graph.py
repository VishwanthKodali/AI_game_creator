"""Build and compile the LangGraph workflow for the Game Builder agent."""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.app.graph.nodes import (
    clarify_node,
    classify_node,
    generate_node,
    plan_node,
)
from src.app.graph.state import GameState


def _route_after_classify(state: GameState) -> str:
    """Conditional edge: decide which node runs after classification."""
    phase = state.get("phase", "clarifying")
    if phase == "planning":
        return "plan"
    if phase == "complete":
        return "__end__"
    return "clarify"


def build_graph() -> StateGraph:
    """Construct and compile the game-builder agent graph.

    Flow
    ----
    START ─► classify ─┬─► clarify ──► END  (wait for user reply)
                        ├─► plan ──► generate ──► END
                        └─► END  (already complete)
    """
    builder = StateGraph(GameState)

    # -- nodes --
    builder.add_node("classify", classify_node)
    builder.add_node("clarify", clarify_node)
    builder.add_node("plan", plan_node)
    builder.add_node("generate", generate_node)

    # -- edges --
    builder.add_edge(START, "classify")
    builder.add_conditional_edges(
        "classify",
        _route_after_classify,
        {
            "clarify": "clarify",
            "plan": "plan",
            "__end__": END,
        },
    )
    builder.add_edge("clarify", END)
    builder.add_edge("plan", "generate")
    builder.add_edge("generate", END)

    # -- compile with in-memory checkpointer for session persistence --
    memory = MemorySaver()
    return builder.compile(checkpointer=memory)
