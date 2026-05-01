"""OpenRouter chat.completions helpers: tool-path kwargs and JSON retry."""

from __future__ import annotations

import atexit
import json
import os
import threading
import time
from copy import deepcopy
from typing import Any

from loguru import logger

from app.core.config import (
    _langsmith_tracing_v2_enabled,
    global_config_loaded_from_config_yaml,
)
from app.utils.config import Environment

_OPENROUTER_JSON_MAX_ATTEMPTS = 3
_OPENROUTER_JSON_BACKOFF_SECONDS = (0.25, 0.75)

_OPEN_LANGSMITH_PARENT_LOCK = threading.Lock()
_OPEN_LANGSMITH_PARENT_RUNS: set[Any] = set()
_ATEXIT_LANGSMITH_PARENT_FLUSH_REGISTERED = False


def _register_open_langsmith_parent_run(root: Any) -> None:
    global _ATEXIT_LANGSMITH_PARENT_FLUSH_REGISTERED
    with _OPEN_LANGSMITH_PARENT_LOCK:
        _OPEN_LANGSMITH_PARENT_RUNS.add(root)
        if not _ATEXIT_LANGSMITH_PARENT_FLUSH_REGISTERED:
            atexit.register(_flush_open_langsmith_parent_runs_on_exit)
            _ATEXIT_LANGSMITH_PARENT_FLUSH_REGISTERED = True


def _unregister_open_langsmith_parent_run(root: Any) -> None:
    with _OPEN_LANGSMITH_PARENT_LOCK:
        _OPEN_LANGSMITH_PARENT_RUNS.discard(root)


def _flush_open_langsmith_parent_runs_on_exit() -> None:
    with _OPEN_LANGSMITH_PARENT_LOCK:
        pending = list(_OPEN_LANGSMITH_PARENT_RUNS)
        _OPEN_LANGSMITH_PARENT_RUNS.clear()
    for run in pending:
        end_companion_turn_root_run_safe(
            run,
            error="process exit before langsmith companion parent run was closed",
            ls_end_source="atexit_open_parent_flush",
        )


class OpenRouterInvalidJsonError(RuntimeError):
    """OpenRouter returned a response body that was not valid JSON."""


def companion_turn_langsmith_parent_enabled() -> bool:
    if global_config_loaded_from_config_yaml.app.environment == Environment.TEST:
        return False
    if not _langsmith_tracing_v2_enabled(global_config_loaded_from_config_yaml):
        return False
    if os.environ.get("LANGSMITH_TRACING_V2", "").strip().lower() != "true":
        return False
    return True


def create_companion_turn_root_run(
    *, inty_trace_id: str, user_msg_uuid: str
) -> Any | None:
    if not companion_turn_langsmith_parent_enabled():
        return None
    try:
        from langsmith.run_trees import RunTree

        root = RunTree(
            name="agentic_companion_user_turn",
            run_type="chain",
            inputs={
                "inty_trace_id": inty_trace_id,
                "user_msg_uuid": user_msg_uuid,
            },
            tags=["agentic_companion", "user_turn"],
        )
        initial_post_ok = True
        initial_post_err = ""
        try:
            root.post()
        except Exception as exc:
            initial_post_ok = False
            initial_post_err = repr(exc)
            logger.debug("companion_turn_langsmith_parent initial post skipped: {}", exc)
        logger.info(
            "langsmith_companion_parent_run created inty_trace_id={} user_msg_uuid={} "
            "ls_trace_id={} ls_run_id={} initial_post_ok={} initial_post_err={!r}",
            inty_trace_id,
            user_msg_uuid,
            companion_turn_langsmith_parent_trace_id_str(root),
            companion_turn_langsmith_parent_run_id_str(root),
            initial_post_ok,
            initial_post_err,
        )
        _register_open_langsmith_parent_run(root)
        return root
    except Exception as exc:
        logger.warning("companion_turn_langsmith_parent create failed: {}", exc)
        return None


def companion_turn_langsmith_parent_trace_id_str(root_run: Any) -> str:
    if root_run is None:
        return ""
    try:
        tid = getattr(root_run, "trace_id", None)
        if tid is None:
            return ""
        return str(tid).strip()
    except Exception:
        return ""


def companion_turn_langsmith_parent_run_id_str(root_run: Any) -> str:
    if root_run is None:
        return ""
    try:
        rid = getattr(root_run, "id", None)
        if rid is None:
            return ""
        return str(rid).strip()
    except Exception:
        return ""


def end_companion_turn_root_run_safe(
    root_run: Any,
    *,
    error: str | None = None,
    outputs: dict[str, Any] | None = None,
    ls_end_source: str = "",
) -> None:
    if root_run is None:
        return
    ls_tid = companion_turn_langsmith_parent_trace_id_str(root_run)
    ls_rid = companion_turn_langsmith_parent_run_id_str(root_run)
    th_name = threading.current_thread().name
    logger.info(
        "langsmith_companion_parent_run end_start ls_end_source={!r} thread={} "
        "ls_trace_id={} ls_run_id={} has_error={}",
        ls_end_source,
        th_name,
        ls_tid,
        ls_rid,
        error is not None,
    )
    try:
        if error is not None:
            root_run.end(error=error)
        elif outputs is not None:
            root_run.end(outputs=outputs)
        else:
            root_run.end()
    except Exception as exc:
        logger.warning(
            "companion_turn_langsmith_parent end failed ls_end_source={!r} thread={} "
            "ls_trace_id={} ls_run_id={} err={}",
            ls_end_source,
            th_name,
            ls_tid,
            ls_rid,
            exc,
        )
        return
    try:
        root_run.patch(exclude_inputs=True)
    except Exception as exc:
        logger.warning(
            "companion_turn_langsmith_parent patch after end failed ls_end_source={!r} "
            "thread={} ls_trace_id={} ls_run_id={} err={}; falling back to post",
            ls_end_source,
            th_name,
            ls_tid,
            ls_rid,
            exc,
        )
        try:
            root_run.post()
        except Exception as exc2:
            logger.warning(
                "companion_turn_langsmith_parent post after patch failure failed "
                "ls_end_source={!r} thread={} ls_trace_id={} ls_run_id={} err={}",
                ls_end_source,
                th_name,
                ls_tid,
                ls_rid,
                exc2,
            )
            _unregister_open_langsmith_parent_run(root_run)
            return
    _unregister_open_langsmith_parent_run(root_run)
    logger.info(
        "langsmith_companion_parent_run end_synced ls_end_source={!r} thread={} "
        "ls_trace_id={} ls_run_id={} has_error={}",
        ls_end_source,
        th_name,
        ls_tid,
        ls_rid,
        error is not None,
    )


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


def _completion_with_langsmith_trace_id(raw: Any) -> Any:
    if langsmith_trace_id_from_completion(raw):
        return raw
    tid = _langsmith_trace_id_from_active_run_tree()
    if not tid:
        return raw
    model_copy = getattr(raw, "model_copy", None)
    if model_copy is None:
        return raw
    try:
        return model_copy(update={"langsmith_trace_id": tid})
    except Exception:
        return raw


def tool_path_chat_completion_kwargs(model: str) -> dict[str, Any]:
    import os

    raw = os.environ.get("INTY_V2_PROTO_TOOL_THINKING")
    if raw is not None and str(raw).strip().lower() in (
        "0",
        "false",
        "no",
        "off",
        "none",
    ):
        return {}

    from app.utils.models_catalog import is_deepseek_on_openrouter, is_gemini_model

    if is_deepseek_on_openrouter(model):
        return {"extra_body": {"reasoning": {"effort": "high", "exclude": True}}}
    if is_gemini_model(model):
        return {"reasoning_effort": "high"}
    return {}


def create_chat_completion_sync(
    client: Any,
    *,
    model: str,
    messages_payload: list[dict[str, Any]],
    tools: list[Any],
    tool_choice: str | None = None,
    response_format: dict[str, Any] | None = None,
) -> Any:
    create_kw: dict[str, Any] = {
        "model": model,
        "messages": deepcopy(messages_payload),
    }
    if response_format is not None:
        create_kw["response_format"] = response_format
    if tools:
        create_kw.update(tool_path_chat_completion_kwargs(model))
        create_kw["tools"] = tools
        create_kw["parallel_tool_calls"] = True
        if tool_choice is not None:
            create_kw["tool_choice"] = tool_choice
    for attempt in range(1, _OPENROUTER_JSON_MAX_ATTEMPTS + 1):
        try:
            raw = client.chat.completions.create(**create_kw)
            return _completion_with_langsmith_trace_id(raw)
        except json.JSONDecodeError as exc:
            retryable = attempt < _OPENROUTER_JSON_MAX_ATTEMPTS
            logger.warning(
                "llm.chat_completions invalid_json_response model={} attempt={}/{} retryable={} err={}",
                model,
                attempt,
                _OPENROUTER_JSON_MAX_ATTEMPTS,
                retryable,
                exc,
            )
            if retryable:
                delay = _OPENROUTER_JSON_BACKOFF_SECONDS[min(attempt - 1, 1)]
                time.sleep(delay)
                continue
            raise OpenRouterInvalidJsonError(
                "OpenRouter returned a non-JSON response body "
                f"for model={model} after {_OPENROUTER_JSON_MAX_ATTEMPTS} attempts."
            ) from exc
