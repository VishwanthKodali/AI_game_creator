from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage
import re
from typing import Dict
from src.app.common.settings import Settings


def _llm(model: str | None = None, temperature: float = 0.7) -> ChatOpenAI:
    """Return a ChatOpenAI instance pointed at the Groq API."""
    return ChatOpenAI(
        model=model or Settings.groq_model_fast,
        api_key=Settings.groq_api_key,
        base_url=Settings.groq_base_url,
        temperature=temperature,
    )


def _conversation_text(messages: list) -> str:
    """Flatten message objects into a readable transcript."""
    lines: list[str] = []
    for msg in messages:
        content = getattr(msg, "content", "")
        if isinstance(msg, HumanMessage):
            lines.append(f"User: {content}")
        elif isinstance(msg, AIMessage):
            lines.append(f"Assistant: {content}")
    return "\n".join(lines)


def parse_generated_files(raw: str, REQUIRED_FILES: list[str]) -> Dict[str, str]:
    """Extract index.html, style.css, and game.js from an LLM response.

    Tries the structured ``---BEGIN / ---END`` delimiters first, then falls
    back to fenced code-blocks.
    """
    files: Dict[str, str] = {}

    # Strategy 1: explicit delimiters
    for fname in REQUIRED_FILES:
        pattern = rf"---BEGIN\s+{re.escape(fname)}\s*---\s*\n(.*?)---END\s+{re.escape(fname)}\s*---"
        match = re.search(pattern, raw, re.DOTALL | re.IGNORECASE)
        if match:
            files[fname] = match.group(1).strip()

    if len(files) == 3:
        return files

    # Strategy 2: fenced code-blocks  (```html ... ```)
    lang_map = {
        REQUIRED_FILES[0]: r"```html\s*\n(.*?)```",
        REQUIRED_FILES[1]: r"```css\s*\n(.*?)```",
        REQUIRED_FILES[2]: r"```(?:javascript|js)\s*\n(.*?)```",
    }
    for fname, pat in lang_map.items():
        if fname not in files:
            m = re.search(pat, raw, re.DOTALL | re.IGNORECASE)
            if m:
                files[fname] = m.group(1).strip()

    return files