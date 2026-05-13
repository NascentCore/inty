"""Load intrinsic-sidekick text from MemoryStore for inner-tick prompt injection.

Kernel inner-tick turns load ``ai_private.jsonl`` via ``prompt_stack`` / ``turn_engine``
(``get_ai_private_jsonl_text_for_prompt``). ``get_ai_private_text_for_prompt`` remains for
``ai_private.md`` only (tests, tooling, optional merge).
"""

from __future__ import annotations

import json
import os
from typing import Any

from loguru import logger

from app.core.companion_harness.memory.memory_store import MemoryStore
from .models import AI_PRIVATE_INJECT_MAX_CHARS

_AI_PRIVATE_MD_REL = "ai_private.md"
_AI_PRIVATE_JSONL_REL = "ai_private.jsonl"


def _default_max_chars() -> int:
    raw = os.environ.get("INTY_V2_PROTO_AI_PRIVATE_MAX_CHARS")
    if raw is None or not str(raw).strip():
        return AI_PRIVATE_INJECT_MAX_CHARS
    return int(str(raw).strip())


def _clip_chars(s: str, cap: int) -> str:
    """Keep prefix within cap (same rule as historical ai_private.md injection)."""
    if cap <= 0:
        return ""
    if len(s) <= cap:
        return s
    return s[: cap - 1] + "..."


def _format_ai_private_jsonl_object(obj: dict[str, Any]) -> str:
    for key in ("text", "content", "note", "body"):
        v = obj.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    try:
        return json.dumps(obj, ensure_ascii=False)
    except TypeError:
        return str(obj)


def get_ai_private_text_for_prompt(
    store: MemoryStore, *, max_chars: int | None = None
) -> str:
    """Read ``ai_private.md`` only.

    Kernel **maintenance** inner-tick turns inject ``ai_private.jsonl`` via
    ``get_ai_private_jsonl_text_for_prompt`` (see ``prompt_stack``). This function
    stays for tooling, tests, and ``get_ai_private_merged_text_for_prompt``.
    """
    cap = max_chars if max_chars is not None else _default_max_chars()
    body = store.read_document_if_exists(_AI_PRIVATE_MD_REL)
    s = body or ""
    return _clip_chars(s, cap)


def get_ai_private_jsonl_text_for_prompt(
    store: MemoryStore, *, max_chars: int | None = None
) -> str:
    """Parse ``ai_private.jsonl`` into plain lines for prompt context (optional layer)."""
    cap = max_chars if max_chars is not None else _default_max_chars()
    raw = store.read_document_if_exists(_AI_PRIVATE_JSONL_REL)
    if not raw or not raw.strip():
        return ""

    lines_out: list[str] = []
    for i, line in enumerate(raw.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            logger.warning("ai_private.jsonl skipped invalid JSON line {}", i)
            continue
        if isinstance(obj, dict):
            lines_out.append(_format_ai_private_jsonl_object(obj))
        else:
            lines_out.append(json.dumps(obj, ensure_ascii=False))

    merged = "\n".join(lines_out)
    return _clip_chars(merged, cap)


def get_ai_private_merged_text_for_prompt(
    store: MemoryStore, *, max_chars: int | None = None
) -> str:
    """Concatenate ``ai_private.md`` then ``ai_private.jsonl`` under one character budget."""
    cap = max_chars if max_chars is not None else _default_max_chars()
    md = get_ai_private_text_for_prompt(store, max_chars=cap)
    jl = get_ai_private_jsonl_text_for_prompt(store, max_chars=cap)
    if not jl.strip():
        return md
    sep = "\n\n---\n\n（ai_private.jsonl）\n\n"
    combined = md.rstrip() + sep + jl.strip()
    return _clip_chars(combined, cap)
