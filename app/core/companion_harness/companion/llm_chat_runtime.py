"""Companion LangSmith parent runs and re-exports for chat completion helpers.

Chat completion sync calls, OpenRouter tool-path kwargs, and LangSmith completion
enrichment live under ``app.core.companion_harness.llm``; this module keeps the
companion turn parent ``RunTree`` lifecycle and stable import paths for callers.
"""

from __future__ import annotations

import atexit
import threading
from typing import Any

from loguru import logger

from app.core.companion_harness.llm.chat_completions import (
    OpenRouterInvalidJsonError,
    create_chat_completion_sync,
)
from app.core.companion_harness.llm.langsmith_completion_enrich import (
    langsmith_llm_run_id_from_completion,
    langsmith_trace_id_from_completion,
)
from app.core.companion_harness.llm.openrouter_tool_params import (
    tool_path_chat_completion_kwargs,
)
from app.core.companion_harness.companion.langsmith_parent_policy import (
    companion_langsmith_parent_run_allowed,
    companion_turn_langsmith_parent_enabled_from_app_config,
)
from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    InnerTickActivity,
)
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.core.companion_harness.companion.turn_track import (
    langsmith_inty_turn_lane_for_companion_track,
    turn_flags_for_track,
)
from app.utils.models_catalog import (
    GenAIModel,
    genai_model_langsmith_meta_subset,
)

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
    chat_model: GenAIModel, tool_model: GenAIModel
) -> bool:
    return (
        chat_model.id_on_provider
        == _LANGSMITH_PARENT_SKIP_PLACEHOLDER_CHAT_MODEL
        and tool_model.id_on_provider
        == _LANGSMITH_PARENT_SKIP_PLACEHOLDER_TOOL_MODEL
    )


def companion_turn_langsmith_parent_enabled() -> bool:
    return companion_turn_langsmith_parent_enabled_from_app_config()


def _langsmith_parent_run_extra_metadata(
    *,
    chat_model: GenAIModel,
    tool_model: GenAIModel,
    user_id: str = "",
    companion_id: str = "",
    runtime_channel: CompanionRuntimeChannel | None = None,
) -> dict[str, Any]:
    """Align with langsmith.wrappers._openai ``ls_model_name`` for trace filtering."""
    cm = chat_model.id_on_provider.strip()
    tm = tool_model.id_on_provider.strip()
    meta: dict[str, Any] = {
        "inty_chat_model": cm,
        "inty_tool_model": tm,
        "inty_chat_model_nickname": chat_model.nickname,
        "inty_tool_model_nickname": tool_model.nickname,
        "inty_chat_model_catalog": genai_model_langsmith_meta_subset(
            chat_model
        ),
        "inty_tool_model_catalog": genai_model_langsmith_meta_subset(
            tool_model
        ),
        "inty_user_id": (user_id or "").strip(),
        "inty_companion_id": (companion_id or "").strip(),
    }
    if runtime_channel is not None:
        meta["inty_runtime_channel"] = runtime_channel.value
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
    inner_tick_activity: InnerTickActivity | None,
    implicit_user_signed_on: bool,
) -> tuple[str, list[str], str, dict[str, Any]]:
    """Return (run name, tags, inty_turn_lane, extra_inputs_for_run_tree).

    Implicit branch: umbrella lane ``implicit_turn`` (隐式信号：当前可为隐式上线，日后追加其它信号时在
    ``extra_in["implicit_signal"]`` 与 tags 上扩展，例如额外 tag ``implicit_<signal>``）。
    """
    uid = (user_id or "").strip() or "unknown"
    cid = (companion_id or "").strip() or "unknown"
    extra_in: dict[str, Any] = {}
    if inner_tick_turn:
        mode = inner_tick_activity or InnerTickActivity.MAINTENANCE
        lane = "inner_tick"
        extra_in["inner_tick_activity"] = mode.value
        name = (
            f"agentic_companion_inner_tick {mode.value} user={uid} agent={cid}"
        )
        tags = ["agentic_companion", "inner_tick"]
        return name, tags, lane, extra_in
    if implicit_user_signed_on:
        lane = "implicit_turn"
        extra_in["implicit_signal"] = "implicit_user_signed_on"
        name = f"agentic_companion_implicit_turn user={uid} agent={cid}"
        tags = [
            "agentic_companion",
            "implicit_turn",
            "implicit_user_signed_on",
        ]
        return name, tags, lane, extra_in
    lane = "explicit_user_message"
    name = f"agentic_companion_user_turn user={uid} agent={cid}"
    tags = ["agentic_companion", "user_turn", "explicit_user_message"]
    return name, tags, lane, extra_in


def create_companion_turn_root_run(
    *,
    inty_trace_id: str,
    user_msg_uuid: str,
    chat_model: GenAIModel,
    tool_model: GenAIModel,
    user_id: str = "",
    companion_id: str = "",
    parent_run_enabled: bool | None = None,
    companion_turn_track: CompanionTurnTrack | None = None,
    inner_tick_turn: bool = False,
    inner_tick_activity: InnerTickActivity | None = None,
    implicit_user_signed_on: bool = False,
    transcript_newest_message_uuid: str | None = None,
    runtime_channel: CompanionRuntimeChannel | None = None,
) -> Any | None:
    enabled = (
        companion_turn_langsmith_parent_enabled()
        if parent_run_enabled is None
        else parent_run_enabled
    )
    if not enabled:
        return None
    if _langsmith_parent_models_are_kernel_test_placeholders(
        chat_model, tool_model
    ):
        logger.debug(
            "companion_turn_langsmith_parent skipped: kernel test placeholder models "
            "chat_model={!r} tool_model={!r}",
            chat_model.id_on_provider,
            tool_model.id_on_provider,
        )
        return None
    try:
        from langsmith.run_trees import RunTree

        uid = (user_id or "").strip()
        cid = (companion_id or "").strip()
        if companion_turn_track is not None:
            inner_tick_turn, route_inner_activity = turn_flags_for_track(
                companion_turn_track
            )
            implicit_user_signed_on = (
                companion_turn_track
                == CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING
            )
            inner_tick_activity = (
                route_inner_activity if inner_tick_turn else None
            )
        run_name, run_tags, turn_lane, lane_inputs = (
            _companion_turn_langsmith_root_descriptor(
                user_id=uid,
                companion_id=cid,
                inner_tick_turn=inner_tick_turn,
                inner_tick_activity=inner_tick_activity,
                implicit_user_signed_on=implicit_user_signed_on,
            )
        )
        if companion_turn_track is not None:
            turn_lane = langsmith_inty_turn_lane_for_companion_track(
                companion_turn_track
            )
        meta = _langsmith_parent_run_extra_metadata(
            chat_model=chat_model,
            tool_model=tool_model,
            user_id=uid,
            companion_id=cid,
            runtime_channel=runtime_channel,
        )
        meta["inty_turn_lane"] = turn_lane
        if inner_tick_turn:
            meta["inner_tick_activity"] = lane_inputs["inner_tick_activity"]
            tail_uuid = (transcript_newest_message_uuid or "").strip()
            if tail_uuid:
                meta["transcript_newest_message_uuid"] = tail_uuid
        if implicit_user_signed_on:
            meta["implicit_signal"] = lane_inputs["implicit_signal"]
        root_inputs: dict[str, Any] = {
            "inty_trace_id": inty_trace_id,
            "user_msg_uuid": user_msg_uuid,
            "chat_model": chat_model.id_on_provider,
            "tool_model": tool_model.id_on_provider,
            "chat_model_catalog": genai_model_langsmith_meta_subset(chat_model),
            "tool_model_catalog": genai_model_langsmith_meta_subset(tool_model),
            "user_id": uid,
            "companion_id": cid,
            "inty_turn_lane": turn_lane,
            **lane_inputs,
        }
        if runtime_channel is not None:
            root_inputs["runtime_channel"] = runtime_channel.value
        if inner_tick_turn:
            tail_uuid = (transcript_newest_message_uuid or "").strip()
            if tail_uuid:
                root_inputs["transcript_newest_message_uuid"] = tail_uuid
        if runtime_channel is not None:
            run_tags = [*run_tags, f"runtime_channel_{runtime_channel.value}"]
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
    return _companion_turn_langsmith_parent_id_str(
        root_run, attr_name="trace_id", id_label="trace_id"
    )


def companion_turn_langsmith_parent_run_id_str(root_run: Any) -> str:
    return _companion_turn_langsmith_parent_id_str(
        root_run, attr_name="id", id_label="run_id"
    )


def _companion_turn_langsmith_parent_id_str(
    root_run: Any, *, attr_name: str, id_label: str
) -> str:
    if root_run is None:
        return ""
    try:
        raw_id = getattr(root_run, attr_name, None)
        if raw_id is None:
            return ""
        return str(raw_id).strip()
    except Exception as exc:
        logger.warning(
            "companion_turn_langsmith_parent {} extraction failed "
            "root_run_type={} err={}",
            id_label,
            type(root_run).__name__,
            exc,
        )
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
