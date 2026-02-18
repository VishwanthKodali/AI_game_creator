"""LangGraph state schema for the Game Builder agent."""

from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages

class GameState(TypedDict):
    """Shared state that flows through every node of the graph.

    Fields
    ------
    messages : list
        Full conversation history (uses ``add_messages`` reducer to append).
    phase : str
        Current agent phase: init | clarifying | planning | generating | complete.
    clarification_count : int
        Number of clarification rounds completed so far.
    clarification_data : dict
        Structured answers to fixed clarification questions:
        - control_type: "mouse" or "keyboard"
        - genre: str
        - winning_condition: str
        - failing_condition: str
        - mechanism: str
    game_plan : str
        Structured development plan produced by the planning node.
    generated_files : dict
        Mapping of filename → content for the final game output.
    """

    messages: Annotated[list, add_messages]
    phase: str
    clarification_count: int
    clarification_data: dict
    game_plan: str
    generated_files: dict
