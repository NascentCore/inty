"""Runtime snapshot for companion_runtime_inspect (ContextVar + optional thread overlay)."""

from __future__ import annotations

import copy
import json
import threading
from contextvars import ContextVar, Token
from typing import Any

from app.core.companion_harness.experience_profile import (
    experience_profile_injects_private_memory,
)

from .llm_chat_runtime import tool_path_chat_completion_kwargs
from .memory_pipeline import MemoryPipelineConfig
from .models import (
    AI_PRIVATE_INJECT_MAX_CHARS,
    TRANSCRIPT_WINDOW_MAX_MESSAGES,
    ContextMeta,
    InnerTickMode,
    _MEMORY_DAY_SUMMARY_INJECT_MAX_CHARS,
    _MEMORY_RAW_INJECT_MAX_CHARS,
    _OPTIONAL_DOC_MAX_CHARS,
)
from .llm_client import CompanionLLMClient
from .memory_store import MemoryStore
from .transcript_compaction import CompactionConfig as TranscriptCompactionConfig

_MAX_TOOL_ROUNDS_SNAPSHOT = 24


_inspect_var: ContextVar[dict[str, Any] | None] = ContextVar(
    "companion_runtime_inspect_bundle", default=None
)
_thread_overlay: threading.local = threading.local()


def runtime_inspect_begin_turn() -> Token[dict[str, Any] | None]:
    return _inspect_var.set(
        {
            "runtime_config": None,
            "last_chat_completion_request": None,
            "scoped_memory_store": None,
        }
    )


def runtime_inspect_end_turn(token: Token[dict[str, Any] | None]) -> None:
    _inspect_var.reset(token)


def runtime_inspect_set_runtime_config(cfg: dict[str, Any]) -> None:
    d = _inspect_var.get()
    if d is not None:
        d["runtime_config"] = cfg


def runtime_inspect_set_scoped_memory_store(store: MemoryStore | None) -> None:
    d = _inspect_var.get()
    if d is not None:
        d["scoped_memory_store"] = store


def runtime_inspect_set_last_chat_completion_request(payload: dict[str, Any]) -> None:
    d = _inspect_var.get()
    if d is not None:
        d["last_chat_completion_request"] = payload
    td = getattr(_thread_overlay, "bundle", None)
    if td is not None:
        td["last_chat_completion_request"] = payload


def runtime_inspect_thread_overlay_begin(initial: dict[str, Any]) -> None:
    _thread_overlay.bundle = initial


def runtime_inspect_thread_overlay_end() -> None:
    _thread_overlay.bundle = None


def runtime_inspect_set_correlation(correlation: dict[str, Any]) -> None:
    """Debug IDs for companion_runtime_inspect output (main turn + tool_background thread)."""
    d = _inspect_var.get()
    if d is not None:
        d["correlation"] = correlation
    td = getattr(_thread_overlay, "bundle", None)
    if td is not None:
        td["correlation"] = correlation


def runtime_inspect_get_correlation_snapshot() -> dict[str, Any] | None:
    """Prefer tool_background overlay, then ContextVar bundle."""
    td = getattr(_thread_overlay, "bundle", None)
    if td is not None:
        c = td.get("correlation")
        if isinstance(c, dict) and c:
            return copy.deepcopy(c)
    d = _inspect_var.get(None)
    if d is not None:
        c2 = d.get("correlation")
        if isinstance(c2, dict) and c2:
            return copy.deepcopy(c2)
    return None


def _bundle_payload_with_store(bundle: dict[str, Any]) -> dict[str, Any] | None:
    if not (
        bundle.get("runtime_config") is not None
        or bundle.get("last_chat_completion_request") is not None
        or bundle.get("scoped_memory_store") is not None
    ):
        return None
    serializable = {k: v for k, v in bundle.items() if k != "scoped_memory_store"}
    return copy.deepcopy(serializable)


def runtime_inspect_get_bundle() -> dict[str, Any] | None:
    d = _inspect_var.get(None)
    if d is not None:
        merged = _bundle_payload_with_store(d)
        if merged is not None:
            return merged
    td = getattr(_thread_overlay, "bundle", None)
    if td is not None:
        return _bundle_payload_with_store(td)
    return None


def runtime_inspect_get_scoped_memory_store() -> MemoryStore | None:
    """Prefer tool_background thread overlay, then the main run_turn ContextVar bundle."""
    td = getattr(_thread_overlay, "bundle", None)
    if td is not None:
        s = td.get("scoped_memory_store")
        if isinstance(s, MemoryStore):
            return s
    d = _inspect_var.get(None)
    if d is not None:
        s2 = d.get("scoped_memory_store")
        if isinstance(s2, MemoryStore):
            return s2
    return None


def _strip_internal_message_keys(msg: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in msg.items() if not str(k).startswith("_")}


def normalize_messages_for_snapshot(
    messages: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    out: list[dict[str, Any]] = []
    for i, m in enumerate(messages):
        if not isinstance(m, dict):
            warnings.append(f"message[{i}]_non_dict")
            out.append({"role": "invalid", "content": repr(m)[:2000]})
            continue
        m2 = _strip_internal_message_keys(m)
        try:
            json.dumps(m2, default=str)
            out.append(copy.deepcopy(m2))
        except (TypeError, ValueError):
            warnings.append(f"message[{i}]")
            out.append(
                {
                    "role": m2.get("role", "unknown"),
                    "content": repr(m2.get("content"))[:8000],
                    "_serialization_fallback": True,
                }
            )
    return out, warnings


def tools_summary_from_openai_tools(tools: list[Any] | None) -> dict[str, Any]:
    if not tools:
        return {"enabled": False, "count": 0, "names": []}
    names: list[str] = []
    for t in tools:
        if isinstance(t, dict) and t.get("type") == "function":
            fn = t.get("function") or {}
            n = fn.get("name")
            if isinstance(n, str) and n:
                names.append(n)
    return {"enabled": True, "count": len(tools), "names": names}


def build_turn_runtime_config_dict(
    *,
    llm_client: CompanionLLMClient,
    mem_cfg: MemoryPipelineConfig,
    context: ContextMeta,
    transcript_llm_window_max_messages: int,
    inner_tick_turn: bool,
    inner_tick_mode: InnerTickMode,
    repository_only_store_text: bool,
    transcript_compaction: TranscriptCompactionConfig | None,
    memory_store_read_document_max_chars_cap: int,
) -> dict[str, Any]:
    cfg = llm_client.config
    llm_dump = cfg.model_dump()
    key = (cfg.api_key or "").strip()
    llm_dump["api_key"] = "***" if key else ""
    rm_chat = llm_client.resolve_model("chat")
    rm_tool = llm_client.resolve_model("tool")
    return {
        "source": "run_turn",
        "context_mode": context.context_mode,
        "experience_profile_injects_private_memory": experience_profile_injects_private_memory(
            context.context_mode
        ),
        "context_ids": {
            "user_id": context.user_id,
            "companion_id": context.companion_id,
            "chat_id": context.chat_id,
        },
        "llm": llm_dump,
        "resolved_model_chat": rm_chat,
        "resolved_model_tool": rm_tool,
        "openrouter_extra_kwargs_chat": tool_path_chat_completion_kwargs(rm_chat),
        "openrouter_extra_kwargs_tool": tool_path_chat_completion_kwargs(rm_tool),
        "llm_call_notes": (
            "Companion kernel does not set temperature or max_tokens in Python when calling "
            "chat.completions; OpenRouter/provider defaults apply."
        ),
        "memory_pipeline": mem_cfg.model_dump(),
        "inner_tick_turn": inner_tick_turn,
        "inner_tick_mode": inner_tick_mode.value,
        "repository_only_store_text": repository_only_store_text,
        "transcript_compaction": (
            transcript_compaction.model_dump()
            if transcript_compaction is not None
            else None
        ),
        "turn_limits": {
            "transcript_llm_window_max_messages": transcript_llm_window_max_messages,
            "transcript_window_default": TRANSCRIPT_WINDOW_MAX_MESSAGES,
            "max_tool_rounds": _MAX_TOOL_ROUNDS_SNAPSHOT,
            "memory_store_read_document_max_chars_cap": (
                memory_store_read_document_max_chars_cap
            ),
            "ai_private_inject_max_chars": AI_PRIVATE_INJECT_MAX_CHARS,
            "memory_raw_inject_max_chars": _MEMORY_RAW_INJECT_MAX_CHARS,
            "memory_day_summary_inject_max_chars": _MEMORY_DAY_SUMMARY_INJECT_MAX_CHARS,
            "optional_doc_max_chars": _OPTIONAL_DOC_MAX_CHARS,
        },
    }


def build_last_chat_completion_request_payload(
    *,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[Any] | None,
    tool_choice: str | None = None,
    response_format_json_schema_name: str | None = None,
) -> dict[str, Any]:
    norm, w = normalize_messages_for_snapshot(messages)
    payload: dict[str, Any] = {
        "model": model,
        "messages": norm,
        "tools_summary": tools_summary_from_openai_tools(tools),
        "openrouter_extra_body": tool_path_chat_completion_kwargs(model),
    }
    if tool_choice is not None:
        payload["tool_choice"] = tool_choice
    if response_format_json_schema_name:
        payload["response_format_json_schema_name"] = response_format_json_schema_name
    if w:
        payload["per_message_warnings"] = w
        payload["messages_serialization_note"] = (
            "Some messages were normalized for JSON (see per_message_warnings)."
        )
    return payload
