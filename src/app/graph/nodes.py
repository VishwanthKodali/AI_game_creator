# """LangGraph node implementations for the Game Builder agent."""

# from __future__ import annotations
# import logging
# from typing import Any, Dict
# from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
# from src.app.graph.prompt import (GENERATE_SYSTEM_PROMPT,PLAN_SYSTEM_PROMPT,)
# from src.app.common.settings import Settings
# from src.app.graph.state import GameState
# from src.app.components.helpers import _llm, parse_generated_files, _conversation_text

# logger = logging.getLogger(__name__)

# MAX_CLARIFICATION_ROUNDS = 3

# # Required game file names
# REQUIRED_FILES = ["index.html", "style.css", "game.js"]

# def _validate_control_type(answer: str) -> str | None:
#     """Validate and normalize control_type answer. Returns None if invalid."""
#     answer_lower = answer.lower()
#     if "mouse" in answer_lower:
#         return "mouse"
#     if "keyboard" in answer_lower:
#         return "keyboard"
#     return None


# def _find_next_unanswered_question(clarification_data: Dict[str, str]) -> str | None:
#     """Find the key of the next unanswered question, or None if all answered."""
#     for key in CLARIFICATION_QUESTIONS.keys():
#         if key not in clarification_data:
#             return key
#     return None


# def _parse_user_answer(
#     messages: list,
#     clarification_data: Dict[str, str]
# ) -> Dict[str, str] | None:
#     """Extract and validate user's answer from the last message.
    
#     Returns updated clarification_data on success, or None if answer is invalid.
#     """
#     if not messages:
#         return clarification_data
    
#     last_msg = messages[-1]
#     if not isinstance(last_msg, HumanMessage):
#         return clarification_data
    
#     next_key = _find_next_unanswered_question(clarification_data)
#     if next_key is None:
#         return clarification_data
    
#     answer = last_msg.content.strip()
    
#     # Validate control_type specifically
#     if next_key == "control_type":
#         validated = _validate_control_type(answer)
#         if validated is None:
#             return None  # Invalid answer
#         answer = validated
    
#     # Store the answer
#     updated_data = clarification_data.copy()
#     updated_data[next_key] = answer
#     return updated_data


# def classify_node(state: GameState) -> Dict[str, Any]:
#     """Decide whether to clarify, collect answers, or proceed to planning."""
    
#     if state.get("phase") == "complete":
#         return {"phase": "complete"}
    
#     clarification_data = state.get("clarification_data", {})
#     messages = state.get("messages", [])
    
#     # Parse answer if we're in the clarifying phase
#     if state.get("phase") == "clarifying":
#         updated_data = _parse_user_answer(messages, clarification_data)
#         if updated_data is None:
#             # Invalid answer, ask again
#             return {"phase": "clarifying"}
#         clarification_data = updated_data
    
#     # Check if all questions are answered
#     if _find_next_unanswered_question(clarification_data) is None:
#         logger.info("All clarification questions answered – proceeding to plan.")
#         return {
#             "phase": "planning",
#             "clarification_data": clarification_data,
#         }
    
#     # Still need more answers
#     return {
#         "phase": "clarifying",
#         "clarification_data": clarification_data,
#     }


# # Fixed clarification questions
# CLARIFICATION_QUESTIONS = {
#     "control_type": "What control type do you want? (Please answer: **mouse** or **keyboard**)",
#     "genre": "What genre of game do you want to create? (e.g., platformer, puzzle, shooter, racing)\n\n*Note: Please keep it simple - this system works best with simple, single-page browser games.*",
#     "mechanism": "What type of game mechanism do you want? (e.g., gun shooting, arrow shooting, jumping, collecting)",
#     "winning_condition": "What is the winning condition to end the game? (e.g., collect all coins, reach the goal, defeat all enemies)",
#     "failing_condition": "What is the failing condition to end the game? (e.g., lose all lives, run out of time, fall off the edge)",
# }


# def clarify_node(state: GameState) -> Dict[str, Any]:
#     """Ask fixed clarification questions in sequence."""
    
#     clarification_data = state.get("clarification_data", {})
    
#     # Find the next unanswered question
#     for key, question in CLARIFICATION_QUESTIONS.items():
#         if key not in clarification_data:
#             return {
#                 "messages": [AIMessage(content=question)],
#                 "phase": "clarifying",
#                 "clarification_count": state.get("clarification_count", 0) + 1,
#             }
    
#     # All questions answered - this shouldn't happen but just in case
#     return {"phase": "planning"}


# def plan_node(state: GameState) -> Dict[str, Any]:
#     """Produce a structured game development plan from clarification JSON."""

#     import json
    
#     clarification_data = state.get("clarification_data", {})
    
#     # Build the JSON requirement string
#     requirements_json = json.dumps(clarification_data, indent=2)
    
#     llm = _llm(Settings.groq_model_power, temperature=0.5)
#     response = llm.invoke([
#         SystemMessage(content=PLAN_SYSTEM_PROMPT),
#         HumanMessage(
#             content=(
#                 f"Game Requirements (JSON):\n```json\n{requirements_json}\n```\n\n"
#                 "Create a detailed game development plan based on these requirements."
#             )
#         ),
#     ])

#     plan_text = response.content
    
#     # Check if the LLM rejected the game as too complex
#     if "too complex" in plan_text.lower() or "i'm sorry" in plan_text.lower():
#         return {
#             "messages": [AIMessage(content=plan_text)],
#             "phase": "complete",  # End the flow here
#             "game_plan": None,
#         }
    
#     return {
#         "messages": [
#             AIMessage(content=f"**Game Plan**\n\n{plan_text}\n\n_Generating your game now…_")
#         ],
#         "phase": "generating",
#         "game_plan": plan_text,
#     }


# def generate_node(state: GameState) -> Dict[str, Any]:
#     """Generate the three game files (index.html, style.css, game.js)."""

#     llm = _llm(Settings.groq_model_power, temperature=0.3)
#     plan = state.get("game_plan", "")
#     transcript = _conversation_text(state["messages"])

#     response = llm.invoke([
#         SystemMessage(content=GENERATE_SYSTEM_PROMPT),
#         HumanMessage(
#             content=(
#                 f"Full conversation:\n{transcript}\n\n"
#                 f"Game Plan:\n{plan}\n\n"
#                 "Generate the complete game files now."
#             )
#         ),
#     ])

#     files = parse_generated_files(response.content, REQUIRED_FILES)

#     # Validate that ALL three required files are present
#     required_files = set(REQUIRED_FILES)
#     missing_files = required_files - set(files.keys())
    
#     if missing_files:
#         missing_list = ", ".join(sorted(missing_files))
#         logger.error(f"Missing files: {missing_list}")
#         logger.error(f"LLM response:\n{response.content[:500]}...")
#         return {
#             "messages": [
#                 AIMessage(
#                     content=(
#                         f"I encountered an issue generating the game files. "
#                         f"Missing: {missing_list}. "
#                         "Let me try again — please send any message to retry."
#                     )
#                 )
#             ],
#             "phase": "planning",  # allow retry
#         }

#     summary_lines = [
#         "**Your game has been generated!**\n",
#         "Files created:",
#     ]
#     for fname in sorted(files):
#         summary_lines.append(f"- `{fname}`")
#     summary_lines.append(
#         "\nDownload the files and open **index.html** in your browser to play!"
#     )

#     return {
#         "messages": [AIMessage(content="\n".join(summary_lines))],
#         "phase": "complete",
#         "generated_files": files,
#     }

"""LangGraph node implementations for the Game Builder agent."""

from __future__ import annotations
import logging
from typing import Any, Dict
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from src.app.graph.prompt import (GENERATE_SYSTEM_PROMPT, PLAN_SYSTEM_PROMPT)
from src.app.common.settings import Settings
from src.app.graph.state import GameState
from src.app.components.helpers import _llm, parse_generated_files, _conversation_text

logger = logging.getLogger(__name__)

MAX_CLARIFICATION_ROUNDS = 3

# Required game file names
REQUIRED_FILES = ["index.html", "style.css", "game.js"]

# ── Clarification Questions ────────────────────────────────────────────────
# Each question is designed to extract a specific, actionable design decision.
# Options are provided so the LLM has concrete, unambiguous values to work with.

CLARIFICATION_QUESTIONS = {
    "genre": (
        "🎮 **What type of game do you want?**\n\n"
        "Choose one:\n"
        "  `1` – 🏃 **Side-scroller / Platformer** (jump over obstacles, reach the end)\n"
        "  `2` – 🎯 **Top-down Shooter** (move freely, shoot enemies from above)\n"
        "  `3` – 🧩 **Puzzle / Clicker** (click or match items to solve challenges)\n"
        "  `4` – ⚡ **Dodge / Survival** (avoid obstacles as long as possible)\n"
        "  `5` – 💎 **Collector** (gather items while avoiding enemies or traps)\n\n"
        "Reply with the number or describe your own idea."
    ),
    "theme": (
        "🎨 **What is the visual theme or setting?**\n\n"
        "Examples:\n"
        "  `1` – 🌌 Space (stars, planets, neon glow)\n"
        "  `2` – 🌲 Forest / Nature (greens, earthy tones)\n"
        "  `3` – 🏙️ City / Cyberpunk (neon lights, dark background)\n"
        "  `4` – 🏖️ Beach / Ocean (blues, sandy colors)\n"
        "  `5` – 🔥 Fantasy / Magic (dark purple, fire, glowing runes)\n\n"
        "Reply with a number or describe your own theme (e.g. 'pirate ship', 'ice cave')."
    ),
    "control_type": (
        "🕹️ **How should the player control the game?**\n\n"
        "  `keyboard` – Arrow keys or WASD to move/aim, Space or Z to shoot/jump\n"
        "  `mouse` – Click to interact, move cursor to aim\n\n"
        "Reply: **keyboard** or **mouse**"
    ),
    "player_goal": (
        "🏆 **What is the player trying to do?** (winning condition)\n\n"
        "Examples:\n"
        "  • Collect 10 stars before time runs out\n"
        "  • Defeat 15 enemies to win\n"
        "  • Survive for 60 seconds\n"
        "  • Reach the end of the level\n"
        "  • Score 500 points\n\n"
        "Describe the **winning condition** in one sentence."
    ),
    "fail_condition": (
        "💀 **How does the player lose?** (failing condition)\n\n"
        "Examples:\n"
        "  • Getting hit 3 times (3 lives)\n"
        "  • Falling off the platform\n"
        "  • Timer reaches zero\n"
        "  • Enemy reaches the bottom of the screen\n\n"
        "Describe the **losing condition** in one sentence."
    ),
    "difficulty": (
        "⚙️ **How hard should the game be?**\n\n"
        "  `easy` – Slow enemies, large hitboxes, forgiving timers — great for casual play\n"
        "  `medium` – Balanced speed and challenge — recommended for most players\n"
        "  `hard` – Fast enemies, tight timing, punishing — for experienced players\n\n"
        "Reply: **easy**, **medium**, or **hard**"
    ),
}

# ── Validation helpers ─────────────────────────────────────────────────────

GENRE_MAP = {
    "1": "side-scroller platformer",
    "2": "top-down shooter",
    "3": "puzzle / clicker",
    "4": "dodge / survival",
    "5": "collector",
}

THEME_MAP = {
    "1": "space (stars, planets, neon glow, dark background)",
    "2": "forest / nature (greens, browns, earthy tones)",
    "3": "city / cyberpunk (neon lights, dark rainy background)",
    "4": "beach / ocean (blues, sandy yellows, bright sky)",
    "5": "fantasy / magic (dark purple, fire effects, glowing runes)",
}

DIFFICULTY_VALUES = {
    "easy": {"enemy_speed": "2px/frame", "hitbox_scale": "1.3x", "lives": 5, "timer_multiplier": 1.5},
    "medium": {"enemy_speed": "4px/frame", "hitbox_scale": "1.1x", "lives": 3, "timer_multiplier": 1.0},
    "hard": {"enemy_speed": "6px/frame", "hitbox_scale": "0.9x", "lives": 1, "timer_multiplier": 0.75},
}


def _validate_control_type(answer: str) -> str | None:
    a = answer.lower()
    if "mouse" in a:
        return "mouse"
    if "keyboard" in a or "key" in a or "wasd" in a or "arrow" in a:
        return "keyboard"
    return None


def _validate_difficulty(answer: str) -> str | None:
    a = answer.lower()
    if "easy" in a or a == "1":
        return "easy"
    if "medium" in a or "normal" in a or a == "2":
        return "medium"
    if "hard" in a or "difficult" in a or a == "3":
        return "hard"
    return None


def _normalize_genre(answer: str) -> str:
    """Map number choice or free text to a genre string."""
    stripped = answer.strip()
    if stripped in GENRE_MAP:
        return GENRE_MAP[stripped]
    return answer  # Free text passthrough


def _normalize_theme(answer: str) -> str:
    """Map number choice or free text to a theme string."""
    stripped = answer.strip()
    if stripped in THEME_MAP:
        return THEME_MAP[stripped]
    return answer  # Free text passthrough


# ── Core helpers ───────────────────────────────────────────────────────────

def _find_next_unanswered_question(clarification_data: Dict[str, str]) -> str | None:
    for key in CLARIFICATION_QUESTIONS.keys():
        if key not in clarification_data:
            return key
    return None


def _parse_user_answer(
    messages: list,
    clarification_data: Dict[str, str],
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
    updated_data = clarification_data.copy()

    if next_key == "control_type":
        validated = _validate_control_type(answer)
        if validated is None:
            return None  # Re-ask
        updated_data[next_key] = validated

    elif next_key == "difficulty":
        validated = _validate_difficulty(answer)
        if validated is None:
            return None  # Re-ask
        # Store both the label and the concrete values
        updated_data[next_key] = validated
        updated_data["difficulty_params"] = str(DIFFICULTY_VALUES[validated])

    elif next_key == "genre":
        updated_data[next_key] = _normalize_genre(answer)

    elif next_key == "theme":
        updated_data[next_key] = _normalize_theme(answer)

    else:
        # player_goal, fail_condition — accept free text
        updated_data[next_key] = answer

    return updated_data


# ── Nodes ──────────────────────────────────────────────────────────────────

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
            return {"phase": "clarifying"}  # Invalid answer — re-ask
        clarification_data = updated_data

    # Check if all questions answered
    if _find_next_unanswered_question(clarification_data) is None:
        logger.info("All clarification questions answered – proceeding to plan.")
        return {
            "phase": "planning",
            "clarification_data": clarification_data,
        }

    return {
        "phase": "clarifying",
        "clarification_data": clarification_data,
    }


def clarify_node(state: GameState) -> Dict[str, Any]:
    """Ask fixed clarification questions in sequence."""

    clarification_data = state.get("clarification_data", {})

    for key, question in CLARIFICATION_QUESTIONS.items():
        if key == "difficulty_params":
            continue  # Internal field, skip
        if key not in clarification_data:
            return {
                "messages": [AIMessage(content=question)],
                "phase": "clarifying",
                "clarification_count": state.get("clarification_count", 0) + 1,
            }

    return {"phase": "planning"}


def plan_node(state: GameState) -> Dict[str, Any]:
    """Produce a structured game development plan from clarification data."""
    import json

    clarification_data = state.get("clarification_data", {})
    requirements_json = json.dumps(clarification_data, indent=2)

    llm = _llm(Settings.groq_model_power, temperature=0.5)
    response = llm.invoke([
        SystemMessage(content=PLAN_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"Game Requirements (JSON):\n```json\n{requirements_json}\n```\n\n"
                "Create a detailed, visually rich game development plan based on these requirements."
            )
        ),
    ])

    plan_text = response.content

    if "too complex" in plan_text.lower() or "i'm sorry" in plan_text.lower():
        return {
            "messages": [AIMessage(content=plan_text)],
            "phase": "complete",
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
                "Generate the complete, visually polished game files now."
            )
        ),
    ])

    files = parse_generated_files(response.content, REQUIRED_FILES)

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
            "phase": "planning",
        }

    summary_lines = [
        "🎮 **Your game has been generated!**\n",
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