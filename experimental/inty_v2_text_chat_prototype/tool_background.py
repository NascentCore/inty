"""Background tool execution queue for async dual-LLM mode."""

from __future__ import annotations

import asyncio
import queue
import re
import threading
import time
import uuid
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from loguru import logger
from openai import APIError, BadRequestError

from app.core.agentic_kernel.tools.runtime import (
    resolve_official_assistant_tool_loop_async,
)

from .client import create_chat_completion, get_client_dual_llm_tool
from .jsonl_db_store import append_jsonl_with_db
from .llm_trace import emit_trace, summarize_completion_response, summarize_messages
from .utc import local_date_str, utc_iso_ts
from .workspace_init_tools import (
    REPL_WRITABLE_RELATIVE_PATHS,
    execute_tool_call,
    openai_assistant_message_dict,
)

_OUTPUT_QUEUE: queue.Queue["ToolOutputEvent"] | None = None
_OUTPUT_QUEUE_LOCK = threading.Lock()
_ACTIVE_THREADS: set[threading.Thread] = set()
_ACTIVE_THREADS_LOCK = threading.Lock()
_BG_TOOL_MAX_ROUNDS = 24
# Fal `generate_image` / `modify_image` tool summaries include `local_path=/abs/path/...`.
_LOCAL_PATH_IN_TOOL = re.compile(r"local_path=(\S+)")
# When the last user message matches, first background completion uses tool_choice=required
# so the tool-side model cannot skip structured tool calls on image/edit intents.
_BG_USER_HINTS_FORCE_TOOLS = re.compile(
    r"(生成图片|生图|文生图|图生图|改图|重画|画一张|来张图|修图|换风格|"
    r"给我画|画个|画一|肖像照|插图|"
    r"generate\s*image|text-?to-?image|image\s*to\s*image|modify\s*image)",
    re.I,
)


def _last_user_message_text(messages: list[dict[str, Any]]) -> str:
    for m in reversed(messages):
        if m.get("role") != "user":
            continue
        c = m.get("content")
        if isinstance(c, str):
            return c.strip()
    return ""


def _background_turn_should_force_tools(user_text: str) -> bool:
    if not user_text:
        return False
    return _BG_USER_HINTS_FORCE_TOOLS.search(user_text) is not None


def _local_paths_from_tool_messages(
    messages: list[dict[str, Any]],
) -> list[str]:
    """Collect absolute paths from tool role messages (dedupe, order preserved)."""
    seen: set[str] = set()
    out: list[str] = []
    for m in messages:
        if m.get("role") != "tool":
            continue
        content = m.get("content")
        if not isinstance(content, str):
            continue
        for match in _LOCAL_PATH_IN_TOOL.finditer(content):
            p = match.group(1)
            if p and p != "(none)" and p not in seen:
                seen.add(p)
                out.append(p)
    return out


def _append_local_image_paths_for_display(assistant_text: str, paths: list[str]) -> str:
    """Append human-readable lines so REPL can show on-disk image paths after async tools."""
    if not paths:
        return assistant_text
    block = "\n".join(paths)
    suffix = f"\n\n（生成图片本地路径）\n{block}"
    if not assistant_text:
        return suffix.strip()
    return assistant_text.rstrip() + suffix


def _insert_system_message(
    openai_messages: list[dict[str, Any]],
    system_message_content: str,
) -> None:
    insertion_index = 0
    while (
        insertion_index < len(openai_messages)
        and openai_messages[insertion_index].get("role") == "system"
    ):
        insertion_index += 1
    openai_messages.insert(
        insertion_index, {"role": "system", "content": system_message_content}
    )


@dataclass(frozen=True)
class ToolOutputEvent:
    workspace: Path
    user_msg_uuid: str
    assistant_msg_uuid: str
    text: str
    ts: str
    elapsed_ms: int


def output_queue() -> queue.Queue[ToolOutputEvent]:
    global _OUTPUT_QUEUE
    with _OUTPUT_QUEUE_LOCK:
        if _OUTPUT_QUEUE is None:
            _OUTPUT_QUEUE = queue.Queue()
        return _OUTPUT_QUEUE


def clear_output_queue() -> None:
    q = output_queue()
    while True:
        try:
            q.get_nowait()
        except queue.Empty:
            return


def push_output_event(event: ToolOutputEvent) -> None:
    output_queue().put(event)


def pop_output_events_nowait(*, workspace: Path) -> list[ToolOutputEvent]:
    root = workspace.resolve()
    out: list[ToolOutputEvent] = []
    q = output_queue()
    parked: list[ToolOutputEvent] = []
    while True:
        try:
            ev = q.get_nowait()
        except queue.Empty:
            break
        if ev.workspace.resolve() == root:
            out.append(ev)
        else:
            parked.append(ev)
    for ev in parked:
        q.put(ev)
    return out


def _register_thread(t: threading.Thread) -> None:
    with _ACTIVE_THREADS_LOCK:
        _ACTIVE_THREADS.add(t)


def _unregister_thread(t: threading.Thread) -> None:
    with _ACTIVE_THREADS_LOCK:
        _ACTIVE_THREADS.discard(t)


def background_tasks_count() -> int:
    with _ACTIVE_THREADS_LOCK:
        return len(_ACTIVE_THREADS)


def _assistant_text_from_completion_response(resp: Any) -> str:
    content = resp.choices[0].message.content
    if not isinstance(content, str):
        return ""
    return content.strip()


def _openai_messages_payload(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{k: v for k, v in m.items() if not k.startswith("_")} for m in messages]


def _log_bg_llm_round_result(
    *,
    round_idx: int,
    model: str,
    resp: Any,
    request_messages: list[dict[str, Any]],
    llm_trace: bool,
    ws_root: Path,
    trace_id: str | None = None,
) -> None:
    ch0 = resp.choices[0]
    fr = getattr(ch0, "finish_reason", None) or "?"
    tool_calls = getattr(ch0.message, "tool_calls", None) or []
    logger.info(
        "repl.turn.bg llm_round={} finish_reason={} tool_calls_n={} model={}",
        round_idx,
        fr,
        len(tool_calls),
        model,
    )
    if llm_trace:
        emit_trace(
            "repl.turn.bg.tool",
            round_idx=round_idx,
            model=model,
            messages=summarize_messages(
                request_messages,
                ws_label=ws_root.name,
                trace_day=local_date_str(),
            ),
            response=summarize_completion_response(resp),
            trace_id=trace_id,
        )


def _append_background_transcript_assistant(
    transcript_path: Path,
    *,
    content: str,
    assistant_msg_uuid: str,
    reply_to: str,
    trace_id: str,
) -> None:
    append_jsonl_with_db(
        transcript_path,
        {
            "role": "assistant",
            "content": content,
            "ts": utc_iso_ts(),
            "uuid": assistant_msg_uuid,
            "source": "tool_bg",
            "reply_to": reply_to,
            "trace_id": trace_id,
        },
    )


def _append_background_log(
    workspace_root: Path,
    *,
    user_msg_uuid: str,
    assistant_msg_uuid: str,
    elapsed_ms: int,
    rounds: int,
    tool_calls_count: int,
) -> None:
    path = workspace_root / "tool_background.jsonl"
    append_jsonl_with_db(
        path,
        {
            "kind": "tool_background_done",
            "ts": utc_iso_ts(),
            "user_msg_uuid": user_msg_uuid,
            "assistant_msg_uuid": assistant_msg_uuid,
            "elapsed_ms": elapsed_ms,
            "rounds": rounds,
            "tool_calls_count": tool_calls_count,
        },
    )


async def _run_background_tool_loop(
    *,
    ws_root: Path,
    request_messages: list[dict[str, Any]],
    tool_model_name: str,
    llm_trace: bool,
    transcript_path: Path,
    user_msg_uuid: str,
    trace_id: str,
    tools: list[Any],
    on_event: Callable[[ToolOutputEvent], None],
    execute_tool_call_fn: Callable[..., Any],
    client: Any | None,
) -> None:
    resolved_client = client if client is not None else get_client_dual_llm_tool()
    t0 = time.perf_counter()
    working_messages = deepcopy(request_messages)
    total_tool_calls = 0
    rounds_used = 0
    active_round = 0

    request_snapshot = deepcopy(working_messages)
    payload = _openai_messages_payload(working_messages)
    force_tools = bool(tools) and _background_turn_should_force_tools(
        _last_user_message_text(working_messages)
    )
    if force_tools:
        try:
            initial_response = await asyncio.to_thread(
                create_chat_completion,
                resolved_client,
                model=tool_model_name,
                messages_payload=payload,
                tools=tools,
                tool_choice="required",
            )
        except (BadRequestError, APIError) as exc:
            logger.warning(
                "repl.turn.bg tool_choice=required rejected, falling back to auto: {}",
                exc,
            )
            initial_response = await asyncio.to_thread(
                create_chat_completion,
                resolved_client,
                model=tool_model_name,
                messages_payload=payload,
                tools=tools,
                tool_choice=None,
            )
    else:
        initial_response = await asyncio.to_thread(
            create_chat_completion,
            resolved_client,
            model=tool_model_name,
            messages_payload=payload,
            tools=tools,
            tool_choice=None,
        )
    rounds_used += 1
    active_round = rounds_used
    _log_bg_llm_round_result(
        round_idx=active_round,
        model=tool_model_name,
        resp=initial_response,
        request_messages=request_snapshot,
        llm_trace=llm_trace,
        ws_root=ws_root,
        trace_id=trace_id,
    )

    initial_tool_calls = (
        getattr(initial_response.choices[0].message, "tool_calls", None) or []
    )
    if not initial_tool_calls:
        logger.debug("repl.turn.bg no_tool_calls skip_transcript")
        return
    total_tool_calls += len(initial_tool_calls)

    async def execute_tool_call(
        name: str, raw_arguments: str
    ) -> tuple[str, str | None]:
        result = await execute_tool_call_fn(
            ws_root,
            name,
            raw_arguments,
            write_allowlist=REPL_WRITABLE_RELATIVE_PATHS,
        )
        return result, None

    async def continue_chat(
        messages_with_tool_results: list[dict[str, Any]],
    ) -> tuple[Any, str | None]:
        nonlocal rounds_used, active_round, total_tool_calls
        if rounds_used >= _BG_TOOL_MAX_ROUNDS:
            raise ValueError(
                f"background tool loop exceeded max rounds: {_BG_TOOL_MAX_ROUNDS}"
            )
        rounds_used += 1
        active_round = rounds_used
        request_snapshot_inner = deepcopy(messages_with_tool_results)
        next_resp = await asyncio.to_thread(
            create_chat_completion,
            resolved_client,
            model=tool_model_name,
            messages_payload=_openai_messages_payload(messages_with_tool_results),
            tools=tools,
        )
        _log_bg_llm_round_result(
            round_idx=active_round,
            model=tool_model_name,
            resp=next_resp,
            request_messages=request_snapshot_inner,
            llm_trace=llm_trace,
            ws_root=ws_root,
            trace_id=trace_id,
        )
        tool_calls = getattr(next_resp.choices[0].message, "tool_calls", None) or []
        total_tool_calls += len(tool_calls)
        return next_resp, None

    try:
        loop_result = await resolve_official_assistant_tool_loop_async(
            response=initial_response,
            openai_messages=working_messages,
            max_tool_call_rounds=_BG_TOOL_MAX_ROUNDS,
            execute_tool_call=execute_tool_call,
            continue_chat=continue_chat,
            build_assistant_tool_call_message=openai_assistant_message_dict,
            insert_system_message=_insert_system_message,
            initial_trace_id=None,
        )
    except ValueError as exc:
        raise RuntimeError(
            f"background tool loop exceeded max rounds: {_BG_TOOL_MAX_ROUNDS}"
        ) from exc

    assistant_text = _assistant_text_from_completion_response(loop_result.response)
    image_paths = _local_paths_from_tool_messages(loop_result.messages)
    display_text = _append_local_image_paths_for_display(assistant_text, image_paths)
    elapsed_ms = int((time.perf_counter() - t0) * 1000.0)
    # 仅当工具链路产出显式非文本数据（当前为图片本地路径）时，才向用户补发 tool_bg。
    # 纯副作用工具（如 user_profile_record / workspace_write_file）避免二次近似文本回复。
    if not image_paths:
        logger.debug(
            "repl.turn.bg suppress_user_visible_output no_explicit_non_text_data "
            "trace_id={} user_msg_uuid={}",
            trace_id,
            user_msg_uuid,
        )
        return
    assistant_msg_uuid = str(uuid.uuid4())
    _append_background_transcript_assistant(
        transcript_path,
        content=display_text,
        assistant_msg_uuid=assistant_msg_uuid,
        reply_to=user_msg_uuid,
        trace_id=trace_id,
    )
    _append_background_log(
        ws_root,
        user_msg_uuid=user_msg_uuid,
        assistant_msg_uuid=assistant_msg_uuid,
        elapsed_ms=elapsed_ms,
        rounds=rounds_used,
        tool_calls_count=total_tool_calls,
    )
    on_event(
        ToolOutputEvent(
            workspace=ws_root,
            user_msg_uuid=user_msg_uuid,
            assistant_msg_uuid=assistant_msg_uuid,
            text=display_text,
            ts=utc_iso_ts(),
            elapsed_ms=elapsed_ms,
        )
    )


def start_tool_background_job(
    *,
    ws_root: Path,
    request_messages: list[dict[str, Any]],
    tool_model_name: str,
    llm_trace: bool,
    transcript_path: Path,
    user_msg_uuid: str,
    trace_id: str,
    tools: list[Any],
    on_event: Callable[[ToolOutputEvent], None] = push_output_event,
    execute_tool_call_fn: Callable[..., Any] = execute_tool_call,
    client: Any | None = None,
) -> None:
    def _runner() -> None:
        try:
            asyncio.run(
                _run_background_tool_loop(
                    ws_root=ws_root,
                    request_messages=request_messages,
                    tool_model_name=tool_model_name,
                    llm_trace=llm_trace,
                    transcript_path=transcript_path,
                    user_msg_uuid=user_msg_uuid,
                    trace_id=trace_id,
                    tools=tools,
                    on_event=on_event,
                    execute_tool_call_fn=execute_tool_call_fn,
                    client=client,
                )
            )
        except BaseException:
            logger.exception("repl.turn.bg job failed")
        finally:
            _unregister_thread(threading.current_thread())

    t = threading.Thread(target=_runner, name="inty-v2-tool-bg", daemon=True)
    _register_thread(t)
    t.start()
