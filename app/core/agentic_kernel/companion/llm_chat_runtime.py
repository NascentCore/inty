"""Companion LangSmith parent runs and re-exports for chat completion helpers.

Chat completion sync calls, OpenRouter tool-path kwargs, and LangSmith completion
enrichment live under ``app.core.agentic_kernel.llm``; this module keeps the
companion turn parent ``RunTree`` lifecycle and stable import paths for callers.
"""

from __future__ import annotations

import atexit
import threading
from typing import Any

from loguru import logger

from app.core.agentic_kernel.llm.chat_completions import (
    OpenRouterInvalidJsonError,
    create_chat_completion_sync,
)
from app.core.agentic_kernel.llm.langsmith_completion_enrich import (
    langsmith_llm_run_id_from_completion,
    langsmith_trace_id_from_completion,
)
from app.core.agentic_kernel.llm.openrouter_tool_params import (
    tool_path_chat_completion_kwargs,
)
from app.core.agentic_kernel.companion.langsmith_parent_policy import (
    companion_langsmith_parent_run_allowed,
    companion_turn_langsmith_parent_enabled_from_app_config,
)
from app.core.agentic_kernel.companion.models import InnerTickMode

_OPEN_LANGSMITH_PARENT_LOCK = threading.Lock()
_OPEN_LANGSMITH_PARENT_RUNS: dict[int, Any] = {}
_ATEXIT_LANGSMITH_PARENT_FLUSH_REGISTERED = False


def _register_open_langsmith_parent_run(root: Any) -> None:
    global _ATEXIT_LANGSMITH_PARENT_FLUSH_REGISTERED
    with _OPEN_LANGSMITH_PARENT_LOCK:
        _OPEN_LANGSMITH_PARENT_RUNS[id(root)] = root
        if not _ATEXIT_LANGSMITH_PARENT_FLUSH_REGISTERED:
            atexit.register(_flush_open_langsmith_parent_runs_on_exit)
            _ATEXIT_LANGSMITH_PARENT_FLUSH_REGISTERED = True


def _unregister_open_langsmith_parent_run(root: Any) -> None:
    if root is None:
        return
    with _OPEN_LANGSMITH_PARENT_LOCK:
        _OPEN_LANGSMITH_PARENT_RUNS.pop(id(root), None)


def _flush_open_langsmith_parent_runs_on_exit() -> None:
    with _OPEN_LANGSMITH_PARENT_LOCK:
        pending = list(_OPEN_LANGSMITH_PARENT_RUNS.values())
        _OPEN_LANGSMITH_PARENT_RUNS.clear()
    for run in pending:
        end_companion_turn_root_run_safe(
            run,
            error="process exit before langsmith companion parent run was closed",
            ls_end_source="atexit_open_parent_flush",
        )


_LANGSMITH_PARENT_SKIP_PLACEHOLDER_CHAT_MODEL = "m/chat"
_LANGSMITH_PARENT_SKIP_PLACEHOLDER_TOOL_MODEL = "m/tool"


def _langsmith_parent_models_are_kernel_test_placeholders(
    chat_model: str, tool_model: str
) -> bool:
    cm = (chat_model or "").strip()
    tm = (tool_model or "").strip()
    return (
        cm == _LANGSMITH_PARENT_SKIP_PLACEHOLDER_CHAT_MODEL
        and tm == _LANGSMITH_PARENT_SKIP_PLACEHOLDER_TOOL_MODEL
    )


def companion_turn_langsmith_parent_enabled() -> bool:
    return companion_turn_langsmith_parent_enabled_from_app_config()


def _langsmith_parent_run_extra_metadata(
    *,
    chat_model: str,
    tool_model: str,
    user_id: str = "",
    companion_id: str = "",
) -> dict[str, Any]:
    """Align with langsmith.wrappers._openai ``ls_model_name`` for trace filtering."""
    cm = (chat_model or "").strip()
    tm = (tool_model or "").strip()
    meta: dict[str, Any] = {
        "inty_chat_model": cm,
        "inty_tool_model": tm,
        "inty_user_id": (user_id or "").strip(),
        "inty_companion_id": (companion_id or "").strip(),
    }
    if cm and tm and cm != tm:
        meta["ls_model_name"] = f"{cm} | {tm}"
    elif cm:
        meta["ls_model_name"] = cm
    elif tm:
        meta["ls_model_name"] = tm
    return meta


def _companion_turn_langsmith_root_descriptor(
    *,
    user_id: str,
    companion_id: str,
    inner_tick_turn: bool,
    inner_tick_mode: InnerTickMode | None,
    implicit_user_signed_on: bool,
) -> tuple[str, list[str], str, dict[str, Any]]:
    """Return (run name, tags, inty_turn_lane, extra_inputs_for_run_tree)."""
    uid = (user_id or "").strip() or "unknown"
    cid = (companion_id or "").strip() or "unknown"
    extra_in: dict[str, Any] = {}
    if inner_tick_turn:
        mode = inner_tick_mode or InnerTickMode.MAINTENANCE
        lane = "inner_tick"
        extra_in["inner_tick_mode"] = mode.value
        name = f"agentic_companion_inner_tick user={uid} agent={cid}"
        tags = ["agentic_companion", "inner_tick"]
        return name, tags, lane, extra_in
    if implicit_user_signed_on:
        lane = "implicit_user_signed_on"
        name = f"agentic_companion_implicit_turn user={uid} agent={cid}"
        tags = ["agentic_companion", "user_turn", "implicit_user_signed_on"]
        return name, tags, lane, extra_in
    lane = "explicit_user_message"
    name = f"agentic_companion_user_turn user={uid} agent={cid}"
    tags = ["agentic_companion", "user_turn", "explicit_user_message"]
    return name, tags, lane, extra_in


def create_companion_turn_root_run(
    *,
    inty_trace_id: str,
    user_msg_uuid: str,
    chat_model: str = "",
    tool_model: str = "",
    user_id: str = "",
    companion_id: str = "",
    parent_run_enabled: bool | None = None,
    inner_tick_turn: bool = False,
    inner_tick_mode: InnerTickMode | None = None,
    implicit_user_signed_on: bool = False,
) -> Any | None:
    enabled = (
        companion_turn_langsmith_parent_enabled()
        if parent_run_enabled is None
        else parent_run_enabled
    )
    if not enabled:
        return None
    cm = (chat_model or "").strip()
    tm = (tool_model or "").strip()
    if _langsmith_parent_models_are_kernel_test_placeholders(cm, tm):
        logger.debug(
            "companion_turn_langsmith_parent skipped: kernel test placeholder models "
            "chat_model={!r} tool_model={!r}",
            cm,
            tm,
        )
        return None
    try:
        from langsmith.run_trees import RunTree

        uid = (user_id or "").strip()
        cid = (companion_id or "").strip()
        run_name, run_tags, turn_lane, lane_inputs = (
            _companion_turn_langsmith_root_descriptor(
                user_id=uid,
                companion_id=cid,
                inner_tick_turn=inner_tick_turn,
                inner_tick_mode=inner_tick_mode,
                implicit_user_signed_on=implicit_user_signed_on,
            )
        )
        meta = _langsmith_parent_run_extra_metadata(
            chat_model=cm,
            tool_model=tm,
            user_id=uid,
            companion_id=cid,
        )
        meta["inty_turn_lane"] = turn_lane
        if inner_tick_turn:
            meta["inner_tick_mode"] = lane_inputs["inner_tick_mode"]
        root_inputs: dict[str, Any] = {
            "inty_trace_id": inty_trace_id,
            "user_msg_uuid": user_msg_uuid,
            "chat_model": cm,
            "tool_model": tm,
            "user_id": uid,
            "companion_id": cid,
            "inty_turn_lane": turn_lane,
            **lane_inputs,
        }
        root = RunTree(
            name=run_name,
            run_type="chain",
            inputs=root_inputs,
            extra={"metadata": meta},
            tags=run_tags,
        )
        initial_post_ok = True
        initial_post_err = ""
        try:
            root.post()
        except Exception as exc:
            initial_post_ok = False
            initial_post_err = repr(exc)
            logger.debug(
                "companion_turn_langsmith_parent initial post skipped: {}", exc
            )
        logger.debug(
            "langsmith_companion_parent_run created inty_trace_id={} user_msg_uuid={} "
            "user_id={} companion_id={} ls_trace_id={} ls_run_id={} "
            "initial_post_ok={} initial_post_err={!r}",
            inty_trace_id,
            user_msg_uuid,
            uid,
            cid,
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
    logger.debug(
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
    logger.debug(
        "langsmith_companion_parent_run end_synced ls_end_source={!r} thread={} "
        "ls_trace_id={} ls_run_id={} has_error={}",
        ls_end_source,
        th_name,
        ls_tid,
        ls_rid,
        error is not None,
    )


__all__ = [
    "OpenRouterInvalidJsonError",
    "companion_langsmith_parent_run_allowed",
    "companion_turn_langsmith_parent_enabled",
    "companion_turn_langsmith_parent_enabled_from_app_config",
    "companion_turn_langsmith_parent_run_id_str",
    "companion_turn_langsmith_parent_trace_id_str",
    "create_chat_completion_sync",
    "create_companion_turn_root_run",
    "end_companion_turn_root_run_safe",
    "langsmith_llm_run_id_from_completion",
    "langsmith_trace_id_from_completion",
    "tool_path_chat_completion_kwargs",
]
