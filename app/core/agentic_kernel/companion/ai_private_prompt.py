"""Read ai_private.md for prompt injection via MemoryStore (no experimental jsonl_db)."""

from __future__ import annotations

import os
from pathlib import Path

from .memory_registry import get_memory_store
from .models import AI_PRIVATE_INJECT_MAX_CHARS


def _default_max_chars() -> int:
    raw = os.environ.get("INTY_V2_PROTO_AI_PRIVATE_MAX_CHARS")
    if raw is None or not str(raw).strip():
        return AI_PRIVATE_INJECT_MAX_CHARS
    return int(str(raw).strip())


def get_ai_private_text_for_prompt(
    workspace_root: Path, *, max_chars: int | None = None
) -> str:
    cap = max_chars if max_chars is not None else _default_max_chars()
    body = get_memory_store(workspace_root).read_document_if_exists("ai_private.md")
    s = body or ""
    if len(s) <= cap:
        return s
    return s[: cap - 1] + "..."
