"""Core chat processing – bridges the API layer and the LangGraph agent."""

from __future__ import annotations

import asyncio
import logging
import pathlib
from typing import Any, Dict, Optional

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph.state import CompiledStateGraph

from src.app.common.settings import Settings

logger = logging.getLogger(__name__)


async def process_chat(
    graph: CompiledStateGraph,
    user_message: str,
    session_id: str,
    user_id: str,
    new_chat: bool = False,
) -> Dict[str, Any]:
    """Run a single turn of the game-builder agent.

    Parameters
    ----------
    graph : CompiledStateGraph
        The compiled LangGraph workflow instance.
    user_message : str
        The latest message from the user.
    session_id : str
        Unique conversation identifier (used as LangGraph *thread_id*).
    user_id : str
        Identifier for the requesting user.
    new_chat : bool
        If ``True``, start a fresh conversation even if one already exists
        for *session_id*.

    Returns
    -------
    dict
        ``phase``, ``assistant_messages``, ``game_plan``, ``generated_files``
    """
    config: Dict[str, Any] = {"configurable": {"thread_id": session_id}}

    # Track existing message count to identify new messages after invocation
    previous_message_count = 0
    has_existing_state = False
    if not new_chat:
        try:
            snapshot = graph.get_state(config)
            existing_messages = snapshot.values.get("messages", [])
            has_existing_state = bool(existing_messages)
            previous_message_count = len(existing_messages)
        except Exception:
            has_existing_state = False

    # Build the input payload.
    if new_chat or not has_existing_state:
        input_state: Dict[str, Any] = {
            "messages": [HumanMessage(content=user_message)],
            "phase": "init",
            "clarification_count": 0,
            "clarification_data": {},
            "game_plan": "",
            "generated_files": {},
        }
    else:
        input_state = {
            "messages": [HumanMessage(content=user_message)],
        }

    # Invoke the graph (synchronous under the hood; run in thread pool to avoid blocking).
    result = await asyncio.to_thread(graph.invoke, input_state, config=config)

    # Extract ONLY NEW assistant replies added during this turn
    all_messages = result.get("messages", [])
    new_messages = all_messages[previous_message_count:]
    
    assistant_messages: list[str] = []
    for msg in new_messages:
        if isinstance(msg, AIMessage):
            assistant_messages.append(msg.content)

    phase: str = result.get("phase", "unknown")
    game_plan: Optional[str] = result.get("game_plan") or None
    generated_files: Dict[str, str] = result.get("generated_files", {})

    # Persist generated files to disk (useful inside Docker volumes).
    if generated_files:
        _save_files(session_id, generated_files)

    return {
        "phase": phase,
        "assistant_messages": assistant_messages,
        "game_plan": game_plan,
        "generated_files": generated_files,
    }


def _save_files(session_id: str, files: Dict[str, str]) -> None:
    """Write generated game files to ``output/<session_id>/``."""
    out = pathlib.Path(Settings.output_dir) / session_id
    out.mkdir(parents=True, exist_ok=True)
    for fname, content in files.items():
        (out / fname).write_text(content, encoding="utf-8")
    logger.info("Game files saved to %s", out)
