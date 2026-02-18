"""Pydantic request / response schemas for the chat endpoint."""

from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel

class ChatRequest(BaseModel):
    question: str
    user_id: str
    session_id: str
    new_chat: bool = False


# ── Response ───────────────────────────────────────────────────────────────

class ResponseEntry(BaseModel):
    role: str
    content: str


class ChatResponse(BaseModel):
    success: bool
    phase: str
    response: List[ResponseEntry]
    game_plan: Optional[str] = None
    generated_files: Optional[Dict[str, str]] = None
    user_id: str
    session_id: str