"""Load intrinsic-sidekick text from MemoryStore for inner-tick prompt injection.

Kernel inner-tick turns load ``ai_private.jsonl`` via ``prompt_stack`` / ``turn_engine``
(``get_ai_private_jsonl_text_for_prompt``). ``get_ai_private_text_for_prompt`` remains for
``ai_private.md`` only (tests, tooling, optional merge).
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from app.core.companion_harness.memory.memory_store import MemoryStore

# TODO(rename-memory-doc): Rename ai_private.md to AI_PRIVATE.md
# All long-term semantic-like memory should be in capital letters.
_AI_PRIVATE_MD_REL = "ai_private.md"

# TODO(rename-memory-doc): Rename ai_private.jsonl to ai_private_updates.jsonl
_AI_PRIVATE_JSONL_REL = "ai_private.jsonl"

AI_PRIVATE_INJECT_MAX_CHARS = 12_000


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
    store: MemoryStore, *, max_chars: int = AI_PRIVATE_INJECT_MAX_CHARS
) -> str:
    """Read ``ai_private.md`` only.

    Kernel **maintenance** inner-tick turns inject ``ai_private.jsonl`` via
    ``get_ai_private_jsonl_text_for_prompt`` (see ``prompt_stack``). This function
    stays for tooling, tests, and ``get_ai_private_merged_text_for_prompt``.
    """
    body = store.read_document_if_exists(_AI_PRIVATE_MD_REL)
    s = body or ""
    return _clip_chars(s, max_chars)


def get_ai_private_jsonl_text_for_prompt(
    store: MemoryStore, *, max_chars: int = AI_PRIVATE_INJECT_MAX_CHARS
) -> str:
    """Parse ``ai_private.jsonl`` into plain lines for prompt context (optional layer)."""
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
    return _clip_chars(merged, max_chars)


def get_ai_private_merged_text_for_prompt(
    store: MemoryStore, *, max_chars: int = AI_PRIVATE_INJECT_MAX_CHARS
) -> str:
    """Concatenate ``ai_private.md`` then ``ai_private.jsonl`` under one character budget."""
    md = get_ai_private_text_for_prompt(store, max_chars=max_chars)
    jl = get_ai_private_jsonl_text_for_prompt(store, max_chars=max_chars)
    if not jl.strip():
        return md
    sep = "\n\n---\n\n（ai_private.jsonl）\n\n"
    combined = md.rstrip() + sep + jl.strip()
    return _clip_chars(combined, max_chars)
