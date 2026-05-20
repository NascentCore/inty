"""Load dotenv for the chat WebSocket REPL (no OpenRouter client)."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

_REPL_ENV_FILE = Path(__file__).resolve().parent / ".env"


def load_prototype_dotenv() -> None:
    """Load only ``tools/inty_v2_repl/.env`` (never the process cwd ``.env``)."""
    load_dotenv(_REPL_ENV_FILE)
