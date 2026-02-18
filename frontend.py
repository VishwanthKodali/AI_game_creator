"""
Streamlit frontend for the Game Builder AI agent.

Communicates with the FastAPI backend over HTTP and displays a chat-based
interface with phase indicators, game preview, and file downloads.
"""
from __future__ import annotations

import os
import uuid
import zipfile
from io import BytesIO

import requests
import streamlit as st
import streamlit.components.v1 as components

# ── Configuration ──────────────────────────────────────────────────────────

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
CHAT_ENDPOINT = f"{BACKEND_URL}/v1/chat"

PHASE_LABELS = {
    "init": ("🟡", "Waiting for input"),
    "clarifying": ("🔵", "Clarifying requirements"),
    "planning": ("🟠", "Planning the game"),
    "generating": ("⚙️", "Generating game code"),
    "complete": ("✅", "Game ready!"),
    "error": ("🔴", "Error"),
    "unknown": ("⚪", "Unknown"),
}

# ── Page config ────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Game Builder AI",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0c29, #302b63, #24243e);
    }
    [data-testid="stSidebar"] * {
        color: #e0e0e0 !important;
    }

    /* Phase badge */
    .phase-badge {
        display: inline-block;
        padding: 4px 14px;
        border-radius: 16px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .phase-clarifying  { background: #1e3a5f; color: #7ec8e3; }
    .phase-planning    { background: #5f3a1e; color: #e3b07e; }
    .phase-generating  { background: #3a5f1e; color: #b0e37e; }
    .phase-complete    { background: #1e5f3a; color: #7ee3b0; }
    .phase-error       { background: #5f1e1e; color: #e37e7e; }

    /* Chat area */
    .block-container { max-width: 900px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session state defaults ─────────────────────────────────────────────────


def _init_state():
    defaults = {
        "session_id": str(uuid.uuid4()),
        "user_id": "user-1",
        "game_number": 1,  # Track game number
        "messages": [
            {
                "role": "assistant",
                "content": "👋 Hello! I'm a simple game creator. I can help you build fun, single-page browser games using vanilla JavaScript.\n\nAre you ready to generate a new game today? Just type **'hi'** or describe your game idea to get started!"
            }
        ],
        "phase": "init",
        "game_plan": None,
        "generated_files": None,
        "initialized": True,  # Track if already initialized
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


_init_state()

# ── Sidebar ────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🎮 Game Builder AI")
    st.caption("Describe a game idea and the agent will clarify, plan, and build it for you.")

    # Phase indicator
    icon, label = PHASE_LABELS.get(
        st.session_state.phase, PHASE_LABELS["unknown"]
    )
    phase_css = f"phase-{st.session_state.phase}"
    st.markdown(
        f'<span class="phase-badge {phase_css}">{icon} {label}</span>',
        unsafe_allow_html=True,
    )

    st.divider()

    if st.button("🆕  New Game", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.game_number = st.session_state.get("game_number", 1) + 1
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "👋 Hello! I'm a simple game creator. I can help you build fun, single-page browser games using vanilla JavaScript.\n\nAre you ready to generate a new game today? Just type **'hi'** or describe your game idea to get started!"
            }
        ]
        st.session_state.phase = "init"
        st.session_state.game_plan = None
        st.session_state.generated_files = None
        st.rerun()

    st.markdown(f"**Game #{st.session_state.get('game_number', 1)}**")

    # ── Downloads (appear after generation) ────────────────────────────
    if st.session_state.generated_files:
        st.divider()
        st.subheader("📥 Download Files")

        files = st.session_state.generated_files

        for fname, content in sorted(files.items()):
            st.download_button(
                label=f"⬇ {fname}",
                data=content,
                file_name=fname,
                mime="text/plain",
                use_container_width=True,
            )

        # ZIP download
        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname, content in files.items():
                zf.writestr(fname, content)
        buf.seek(0)
        st.download_button(
            label="⬇ Download All (.zip)",
            data=buf.getvalue(),
            file_name="game.zip",
            mime="application/zip",
            use_container_width=True,
        )

# ── Chat history ───────────────────────────────────────────────────────────

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Game preview (shown after generation) ──────────────────────────────────

if st.session_state.generated_files:
    with st.expander("🕹️  Preview Game", expanded=False):
        files = st.session_state.generated_files
        html_content = files.get("index.html", "")
        css_content = files.get("style.css", "")
        js_content = files.get("game.js", "")

        # Build a self-contained HTML page for the iframe preview
        combined = html_content
        if css_content and "<style>" not in combined.lower():
            combined = combined.replace(
                "</head>",
                f"<style>{css_content}</style></head>",
            )
        if css_content:
            combined = combined.replace(
                '<link rel="stylesheet" href="style.css">',
                f"<style>{css_content}</style>",
            )
            combined = combined.replace(
                "<link rel='stylesheet' href='style.css'>",
                f"<style>{css_content}</style>",
            )
        if js_content:
            combined = combined.replace(
                '<script src="game.js"></script>',
                f"<script>{js_content}</script>",
            )
            combined = combined.replace(
                "<script src='game.js'></script>",
                f"<script>{js_content}</script>",
            )
        components.html(combined, height=650, scrolling=True)

# ── Chat input ─────────────────────────────────────────────────────────────

if prompt := st.chat_input("Describe your game idea…"):
    # Add user message to session state
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Call backend
    is_new = len(st.session_state.messages) == 1
    payload = {
        "question": prompt,
        "user_id": st.session_state.user_id,
        "session_id": st.session_state.session_id,
        "new_chat": is_new,
    }

    with st.spinner("Thinking…"):
        try:
            resp = requests.post(CHAT_ENDPOINT, json=payload, timeout=300)
            resp.raise_for_status()
            data = resp.json()

            st.session_state.phase = data.get("phase", "unknown")

            if data.get("game_plan"):
                st.session_state.game_plan = data["game_plan"]

            if data.get("generated_files"):
                st.session_state.generated_files = data["generated_files"]

            # Add assistant replies to session state
            for entry in data.get("response", []):
                content = entry.get("content", "")
                st.session_state.messages.append(
                    {"role": "assistant", "content": content}
                )

        except requests.exceptions.ConnectionError:
            err = "Cannot reach the backend. Is the FastAPI server running?"
            st.session_state.messages.append(
                {"role": "assistant", "content": err}
            )
        except Exception as exc:
            err = f"Unexpected error: {exc}"
            st.session_state.messages.append(
                {"role": "assistant", "content": err}
            )

    st.rerun()



