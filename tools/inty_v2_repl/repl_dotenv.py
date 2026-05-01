"""Load dotenv for the chat WebSocket REPL (no OpenRouter client)."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


def load_prototype_dotenv() -> None:
    """Load cwd `.env` first, then `tools/inty_v2_repl/.env` for keys still unset."""
    load_dotenv()
    load_dotenv(Path(__file__).resolve().parent / ".env")
