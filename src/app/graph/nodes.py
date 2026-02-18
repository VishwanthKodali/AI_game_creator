"""LangGraph node implementations for the Game Builder agent."""

from __future__ import annotations
import logging
from typing import Any, Dict
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from src.app.graph.prompt import (GENERATE_SYSTEM_PROMPT,PLAN_SYSTEM_PROMPT,)
from src.app.common.settings import Settings
from src.app.graph.state import GameState
from src.app.components.helpers import _llm, parse_generated_files, _conversation_text

logger = logging.getLogger(__name__)

MAX_CLARIFICATION_ROUNDS = 3

# Required game file names
REQUIRED_FILES = ["index.html", "style.css", "game.js"]

def _validate_control_type(answer: str) -> str | None:
    """Validate and normalize control_type answer. Returns None if invalid."""
    answer_lower = answer.lower()
    if "mouse" in answer_lower:
        return "mouse"
    if "keyboard" in answer_lower:
        return "keyboard"
    return None


def _find_next_unanswered_question(clarification_data: Dict[str, str]) -> str | None:
    """Find the key of the next unanswered question, or None if all answered."""
    for key in CLARIFICATION_QUESTIONS.keys():
        if key not in clarification_data:
            return key
    return None


def _parse_user_answer(
    messages: list,
    clarification_data: Dict[str, str]
) -> Dict[str, str] | None:
    """Extract and validate user's answer from the last message.
    
    Returns updated clarification_data on success, or None if answer is invalid.
    """
    if not messages:
        return clarification_data
    
    last_msg = messages[-1]
    if not isinstance(last_msg, HumanMessage):
        return clarification_data
    
    next_key = _find_next_unanswered_question(clarification_data)
    if next_key is None:
        return clarification_data
    
    answer = last_msg.content.strip()
    
    # Validate control_type specifically
    if next_key == "control_type":
        validated = _validate_control_type(answer)
        if validated is None:
            return None  # Invalid answer
        answer = validated
    
    # Store the answer
    updated_data = clarification_data.copy()
    updated_data[next_key] = answer
    return updated_data


def classify_node(state: GameState) -> Dict[str, Any]:
    """Decide whether to clarify, collect answers, or proceed to planning."""
    
    if state.get("phase") == "complete":
        return {"phase": "complete"}
    
    clarification_data = state.get("clarification_data", {})
    messages = state.get("messages", [])
    
    # Parse answer if we're in the clarifying phase
    if state.get("phase") == "clarifying":
        updated_data = _parse_user_answer(messages, clarification_data)
        if updated_data is None:
            # Invalid answer, ask again
            return {"phase": "clarifying"}
        clarification_data = updated_data
    
    # Check if all questions are answered
    if _find_next_unanswered_question(clarification_data) is None:
        logger.info("All clarification questions answered – proceeding to plan.")
        return {
            "phase": "planning",
            "clarification_data": clarification_data,
        }
    
    # Still need more answers
    return {
        "phase": "clarifying",
        "clarification_data": clarification_data,
    }


# Fixed clarification questions
CLARIFICATION_QUESTIONS = {
    "control_type": "What control type do you want? (Please answer: **mouse** or **keyboard**)",
    "genre": "What genre of game do you want to create? (e.g., platformer, puzzle, shooter, racing)\n\n*Note: Please keep it simple - this system works best with simple, single-page browser games.*",
    "mechanism": "What type of game mechanism do you want? (e.g., gun shooting, arrow shooting, jumping, collecting)",
    "winning_condition": "What is the winning condition to end the game? (e.g., collect all coins, reach the goal, defeat all enemies)",
    "failing_condition": "What is the failing condition to end the game? (e.g., lose all lives, run out of time, fall off the edge)",
}


def clarify_node(state: GameState) -> Dict[str, Any]:
    """Ask fixed clarification questions in sequence."""
    
    clarification_data = state.get("clarification_data", {})
    
    # Find the next unanswered question
    for key, question in CLARIFICATION_QUESTIONS.items():
        if key not in clarification_data:
            return {
                "messages": [AIMessage(content=question)],
                "phase": "clarifying",
                "clarification_count": state.get("clarification_count", 0) + 1,
            }
    
    # All questions answered - this shouldn't happen but just in case
    return {"phase": "planning"}


def plan_node(state: GameState) -> Dict[str, Any]:
    """Produce a structured game development plan from clarification JSON."""

    import json
    
    clarification_data = state.get("clarification_data", {})
    
    # Build the JSON requirement string
    requirements_json = json.dumps(clarification_data, indent=2)
    
    llm = _llm(Settings.groq_model_power, temperature=0.5)
    response = llm.invoke([
        SystemMessage(content=PLAN_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"Game Requirements (JSON):\n```json\n{requirements_json}\n```\n\n"
                "Create a detailed game development plan based on these requirements."
            )
        ),
    ])

    plan_text = response.content
    
    # Check if the LLM rejected the game as too complex
    if "too complex" in plan_text.lower() or "i'm sorry" in plan_text.lower():
        return {
            "messages": [AIMessage(content=plan_text)],
            "phase": "complete",  # End the flow here
            "game_plan": None,
        }
    
    return {
        "messages": [
            AIMessage(content=f"**Game Plan**\n\n{plan_text}\n\n_Generating your game now…_")
        ],
        "phase": "generating",
        "game_plan": plan_text,
    }


def generate_node(state: GameState) -> Dict[str, Any]:
    """Generate the three game files (index.html, style.css, game.js)."""

    llm = _llm(Settings.groq_model_power, temperature=0.3)
    plan = state.get("game_plan", "")
    transcript = _conversation_text(state["messages"])

    response = llm.invoke([
        SystemMessage(content=GENERATE_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"Full conversation:\n{transcript}\n\n"
                f"Game Plan:\n{plan}\n\n"
                "Generate the complete game files now."
            )
        ),
    ])

    files = parse_generated_files(response.content, REQUIRED_FILES)

    # Validate that ALL three required files are present
    required_files = set(REQUIRED_FILES)
    missing_files = required_files - set(files.keys())
    
    if missing_files:
        missing_list = ", ".join(sorted(missing_files))
        logger.error(f"Missing files: {missing_list}")
        logger.error(f"LLM response:\n{response.content[:500]}...")
        return {
            "messages": [
                AIMessage(
                    content=(
                        f"I encountered an issue generating the game files. "
                        f"Missing: {missing_list}. "
                        "Let me try again — please send any message to retry."
                    )
                )
            ],
            "phase": "planning",  # allow retry
        }

    summary_lines = [
        "**Your game has been generated!**\n",
        "Files created:",
    ]
    for fname in sorted(files):
        summary_lines.append(f"- `{fname}`")
    summary_lines.append(
        "\nDownload the files and open **index.html** in your browser to play!"
    )

    return {
        "messages": [AIMessage(content="\n".join(summary_lines))],
        "phase": "complete",
        "generated_files": files,
    }
