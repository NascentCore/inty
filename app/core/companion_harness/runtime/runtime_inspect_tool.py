"""Implementation of companion_runtime_inspect MemoryStore snapshot tool.

Registers a LangSmith ``@traceable`` span around the tool entrypoint so tool-path
executions appear in traces; large JSON outputs are summarized via ``process_outputs``.
"""

from __future__ import annotations

import json
from typing import Any

from langsmith import traceable

from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.runtime.runtime_events import read_runtime_events
from app.core.companion_harness.runtime.runtime_inspect_context import (
    runtime_inspect_get_bundle,
    runtime_inspect_get_correlation_snapshot,
    runtime_inspect_get_scoped_memory_store,
)
from app.core.companion_harness.runtime.utc import local_date_str

_LANGSMITH_OUTPUT_PREVIEW_CHARS = 6000


def _langsmith_process_outputs_runtime_inspect(result: str) -> dict[str, Any]:
    """Shrink traced outputs: full inspect JSON can reach ``max_chars_llm_messages``."""
    if not isinstance(result, str):
        return {
            "char_count": None,
            "preview": repr(result)[:500],
            "truncated": True,
        }
    n = len(result)
    cap = _LANGSMITH_OUTPUT_PREVIEW_CHARS
    if n <= cap:
        return {"char_count": n, "preview": result, "truncated": False}
    return {
        "char_count": n,
        "preview": result[:cap] + "\n...[truncated for langsmith]",
        "truncated": True,
    }


def _parse_optional_int(raw: Any, *, default: int, minimum: int) -> int:
    if raw is None:
        return default
    if isinstance(raw, bool):
        raise ValueError("must be an integer or omitted")
    if isinstance(raw, int):
        n = raw
    elif isinstance(raw, float) and raw.is_integer():
        n = int(raw)
    else:
        raise ValueError("must be an integer or omitted")
    if n < minimum:
        raise ValueError(f"must be >= {minimum}")
    return n


def _parse_optional_bool(raw: Any, *, default: bool) -> bool:
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        s = raw.strip().lower()
        if s in ("1", "true", "yes", "on"):
            return True
        if s in ("0", "false", "no", "off"):
            return False
    raise ValueError("must be a boolean or omitted")


def _truncate_text(s: str, max_chars: int) -> tuple[str, bool]:
    if len(s) <= max_chars:
        return s, False
    return s[: max_chars - 20] + "\n...[truncated]", True


def _truncate_messages_for_max_chars(
    messages: list[dict[str, Any]], max_total: int
) -> tuple[list[dict[str, Any]], bool]:
    m = [dict(x) for x in messages]
    trunc = False
    for _ in range(512):
        if len(json.dumps(m, ensure_ascii=False, default=str)) <= max_total:
            return m, trunc
        best_i = -1
        best_len = 0
        for i, row in enumerate(m):
            c = row.get("content")
            if isinstance(c, str) and len(c) > best_len:
                best_len = len(c)
                best_i = i
        if best_i >= 0 and best_len > 400:
            new_len = max(400, best_len // 2)
            c0 = m[best_i]["content"]
            if not isinstance(c0, str):
                raise TypeError("selected message content must be a string")
            m[best_i]["content"] = c0[:new_len] + "\n...[truncated]"
            m[best_i]["_content_truncated_for_size"] = True
            trunc = True
            continue
        if len(m) <= 1:
            return (
                [
                    {
                        "role": "system",
                        "content": "[messages omitted: max_chars_llm_messages exceeded]",
                    }
                ],
                True,
            )
        m = m[len(m) // 10 :] or m[:1]
        trunc = True
    return m, True


def _read_store_optional(
    store: MemoryStore, rel: str, *, max_chars: int
) -> dict[str, Any]:
    raw = store.read_document_if_exists(rel)
    if raw is None:
        return {"relative_path": rel, "missing": True, "text": ""}
    text, trunc = _truncate_text(raw, max_chars)
    return {
        "relative_path": rel,
        "missing": False,
        "truncated": trunc,
        "char_count": len(raw),
        "text": text,
    }


@traceable(
    name="companion_runtime_inspect",
    run_type="tool",
    process_outputs=_langsmith_process_outputs_runtime_inspect,
)
def tool_companion_runtime_inspect(
    store: MemoryStore, arguments: dict[str, Any]
) -> str:
    max_chars_per_doc = _parse_optional_int(
        arguments.get("max_chars_per_doc"), default=8000, minimum=100
    )
    max_chars_llm_messages = _parse_optional_int(
        arguments.get("max_chars_llm_messages"), default=120_000, minimum=1000
    )
    include_store_documents = _parse_optional_bool(
        arguments.get("include_store_documents"), default=True
    )
    max_runtime_events = _parse_optional_int(
        arguments.get("max_runtime_events"), default=20, minimum=0
    )
    bundle = runtime_inspect_get_bundle()
    corr = runtime_inspect_get_correlation_snapshot()
    out: dict[str, Any] = {
        "runtime_config": None,
        "last_chat_completion_request": None,
    }
    if corr is not None:
        out["correlation"] = corr
    if bundle is None:
        out["runtime_unavailable_reason"] = (
            "No runtime inspect bundle (outside run_turn/tool_background or inspect scope not set)."
        )
    else:
        out["runtime_config"] = bundle.get("runtime_config")
        last = bundle.get("last_chat_completion_request")
        if isinstance(last, dict):
            msgs = last.get("messages")
            if isinstance(msgs, list):
                msgs2, trunc = _truncate_messages_for_max_chars(
                    [m for m in msgs if isinstance(m, dict)],
                    max_chars_llm_messages,
                )
                last = {**last, "messages": msgs2, "messages_truncated": trunc}
            out["last_chat_completion_request"] = last
        else:
            out["last_chat_completion_request"] = last

    eff_store = runtime_inspect_get_scoped_memory_store() or store
    out["runtime_events"] = read_runtime_events(eff_store, limit=max_runtime_events)

    if include_store_documents:
        day = local_date_str()
        out["store_documents"] = {
            "context_json": _read_store_optional(
                eff_store, "context.json", max_chars=max_chars_per_doc
            ),
            "IDENTITY.md": _read_store_optional(
                eff_store, "IDENTITY.md", max_chars=max_chars_per_doc
            ),
            "SOUL.md": _read_store_optional(
                eff_store, "SOUL.md", max_chars=max_chars_per_doc
            ),
            "USER.md": _read_store_optional(
                eff_store, "USER.md", max_chars=max_chars_per_doc
            ),
            "MEMORY.md": _read_store_optional(
                eff_store, "MEMORY.md", max_chars=max_chars_per_doc
            ),
            f"memory/daily/{day}.md": _read_store_optional(
                eff_store, f"memory/daily/{day}.md", max_chars=max_chars_per_doc
            ),
            f"memory/{day}.md": _read_store_optional(
                eff_store, f"memory/{day}.md", max_chars=max_chars_per_doc
            ),
        }
        state: dict[str, Any] = {}
        for prefix in (".companion", ".inty_v2"):
            mp = f"{prefix}_memory_pipeline.json"
            cc = f"{prefix}_context_compaction_state.json"
            if eff_store.read_document_if_exists(mp) is not None:
                raw = eff_store.read_document_if_exists(mp)
                if raw is not None:
                    state[mp] = raw[:max_chars_per_doc]
            if eff_store.read_document_if_exists(cc) is not None:
                raw2 = eff_store.read_document_if_exists(cc)
                if raw2 is not None:
                    state[cc] = raw2[:max_chars_per_doc]
        out["store_state_json"] = state

    out["notes"] = (
        "For self-check only; reply to the user in natural language without dumping raw JSON. "
        "include_full_tools_schema is not implemented; use tools_summary in last_chat_completion_request. "
        "TOOLS / SIGNIFICANCE_PERCEPTION operator guidance are fixed package templates in PromptBundle, "
        "not authoritative MemoryStore documents here; importance scoring contract and consumers are "
        "documented in significance_perception.py module docstring."
    )
    return json.dumps(out, ensure_ascii=False, indent=2) + "\n"
