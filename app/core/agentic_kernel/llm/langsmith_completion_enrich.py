"""LangSmith helpers for wrapped OpenAI chat completions: patch + response field enrich."""

from __future__ import annotations

import contextvars
from typing import Any

from loguru import logger

_LS_WRAPPED_LLM_RUN_ID: contextvars.ContextVar[str] = contextvars.ContextVar(
    "inty_ls_wrapped_llm_run_id", default=""
)
_LS_HANDLE_CONTAINER_END_PATCHED = False


def reset_wrapped_llm_run_id_for_completion_attempt() -> None:
    """Clear captured LLM run id before each chat.completions attempt (matches prior behavior)."""
    _LS_WRAPPED_LLM_RUN_ID.set("")


def _ensure_langsmith_handle_container_end_patch() -> None:
    """Capture wrap_openai LLM RunTree id from the trace container (not get_current_run_tree)."""
    global _LS_HANDLE_CONTAINER_END_PATCHED
    if _LS_HANDLE_CONTAINER_END_PATCHED:
        return
    try:
        from langsmith import run_helpers as ls_rh

        _orig = ls_rh._handle_container_end

        def _inty_handle_container_end(
            container: Any,
            outputs: Any = None,
            error: Any = None,
            outputs_processor: Any = None,
        ) -> None:
            try:
                if outputs_processor is not None and isinstance(container, dict):
                    nr = container.get("new_run")
                    if nr is not None and getattr(nr, "run_type", None) == "llm":
                        rid = getattr(nr, "id", None)
                        if rid is not None:
                            s = str(rid).strip()
                            if s:
                                _LS_WRAPPED_LLM_RUN_ID.set(s)
            except Exception:
                pass
            return _orig(
                container,
                outputs=outputs,
                error=error,
                outputs_processor=outputs_processor,
            )

        ls_rh._handle_container_end = _inty_handle_container_end
        _LS_HANDLE_CONTAINER_END_PATCHED = True
    except Exception as exc:
        logger.debug("langsmith _handle_container_end patch skipped: {}", exc)


def langsmith_llm_run_id_from_completion(resp: Any) -> str:
    """LangSmith ``agentic_companion_*`` LLM run uuid (child under companion parent chain)."""
    try:
        v = getattr(resp, "langsmith_llm_run_id", None)
        if v is None:
            return ""
        return str(v).strip()
    except Exception:
        return ""


def langsmith_trace_id_from_completion(resp: Any) -> str:
    """Reads optional ``langsmith_trace_id`` copied onto the ChatCompletion by ``create_chat_completion_sync``."""
    try:
        v = getattr(resp, "langsmith_trace_id", None)
        if v is None:
            return ""
        return str(v).strip()
    except Exception:
        return ""


def _langsmith_trace_id_from_active_run_tree() -> str:
    """Best-effort trace id from LangSmith active run (tracing_context parent or nested span)."""
    try:
        from langsmith.run_helpers import get_current_run_tree

        rt = get_current_run_tree()
        if rt is None:
            return ""
        tid = getattr(rt, "trace_id", None)
        if tid is None or not str(tid).strip() or str(tid).strip().lower() == "none":
            tid = getattr(rt, "id", None)
        if tid is None:
            return ""
        return str(tid).strip()
    except Exception:
        return ""


def completion_with_langsmith_trace_id(raw: Any) -> Any:
    existing_tid = langsmith_trace_id_from_completion(raw)
    tid = existing_tid or _langsmith_trace_id_from_active_run_tree()
    llm_rid = (_LS_WRAPPED_LLM_RUN_ID.get() or "").strip()

    if not tid and not llm_rid:
        return raw
    model_copy = getattr(raw, "model_copy", None)
    if model_copy is None:
        return raw
    updates: dict[str, Any] = {}
    if tid and not existing_tid:
        updates["langsmith_trace_id"] = tid
    if llm_rid:
        updates["langsmith_llm_run_id"] = llm_rid
    if not updates:
        return raw
    try:
        return model_copy(update=updates)
    except Exception:
        return raw


_ensure_langsmith_handle_container_end_patch()
