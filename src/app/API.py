"""FastAPI application entry-point."""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.common.settings import validate_settings
from src.app.v1.routers.chat import router as chat_router
from src.app.graph.graph import build_graph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_settings()
    logger.info("Game Builder AI backend starting …")
    logger.info("Building LangGraph workflow…")
    app.state.graph = build_graph()
    logger.info("Graph built and ready")
    yield
    logger.info("Game Builder AI-backend shutting down …")


app = FastAPI(
    title="Game Builder AI",
    description="Agentic game-creation backend powered by LangGraph + Groq",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)


@app.get("/health")
async def health():
    return {"status": "ok"}