"""Chat router – single POST endpoint consumed by the Streamlit frontend."""
from __future__ import annotations
import logging
import traceback
from fastapi import APIRouter, Request
from src.app.core.user_chat import process_chat
from src.app.v1.models import ChatRequest, ChatResponse, ResponseEntry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["chat"])

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request) -> ChatResponse:
    """Accept a user message and return the agent's reply."""
    try:
        result = await process_chat(
            graph=req.app.state.graph,
            user_message=request.question,
            session_id=request.session_id,
            user_id=request.user_id,
            new_chat=request.new_chat,
        )

        entries = [
            ResponseEntry(role="assistant", content=msg)
            for msg in result.get("assistant_messages", [])
        ]

        return ChatResponse(
            success=True,
            phase=result.get("phase", "unknown"),
            response=entries,
            game_plan=result.get("game_plan"),
            generated_files=result.get("generated_files") or None,
            user_id=request.user_id,
            session_id=request.session_id,
        )

    except Exception as exc:
        logger.error("Chat error: %s\n%s", exc, traceback.format_exc())
        return ChatResponse(
            success=False,
            phase="error",
            response=[
                ResponseEntry(role="assistant", content=f"Error: {exc}")
            ],
            user_id=request.user_id,
            session_id=request.session_id,
        )