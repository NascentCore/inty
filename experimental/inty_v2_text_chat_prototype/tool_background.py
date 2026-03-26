"""Background tool execution queue for async dual-LLM mode."""

from __future__ import annotations

import asyncio
import queue
import threading
import time
import uuid
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from loguru import logger

from .file_store import append_jsonl
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


def _chat_completion_create(
    client: Any,
    *,
    model: str,
    messages_payload: list[dict[str, Any]],
    tools: list[Any],
) -> Any:
    create_kw: dict[str, Any] = {"model": model, "messages": deepcopy(messages_payload)}
    if tools:
        create_kw["tools"] = tools
        create_kw["parallel_tool_calls"] = True
    return client.chat.completions.create(**create_kw)


def _log_bg_llm_round_result(
    *,
    round_idx: int,
    model: str,
    resp: Any,
    request_messages: list[dict[str, Any]],
    llm_trace: bool,
    ws_root: Path,
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
        )


def _append_background_transcript_assistant(
    transcript_path: Path,
    *,
    content: str,
    assistant_msg_uuid: str,
    reply_to: str,
) -> None:
    append_jsonl(
        transcript_path,
        {
            "role": "assistant",
            "content": content,
            "ts": utc_iso_ts(),
            "uuid": assistant_msg_uuid,
            "source": "tool_bg",
            "reply_to": reply_to,
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
    append_jsonl(
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
    tools: list[Any],
    on_event: Callable[[ToolOutputEvent], None],
    execute_tool_call_fn: Callable[..., Any],
    client: Any | None,
) -> None:
    from .client import get_client

    resolved_client = client if client is not None else get_client()
    t0 = time.perf_counter()
    working_messages = deepcopy(request_messages)
    total_tool_calls = 0

    for round_idx in range(1, _BG_TOOL_MAX_ROUNDS + 1):
        request_snapshot = deepcopy(working_messages)
        resp = await asyncio.to_thread(
            _chat_completion_create,
            resolved_client,
            model=tool_model_name,
            messages_payload=_openai_messages_payload(working_messages),
            tools=tools,
        )
        _log_bg_llm_round_result(
            round_idx=round_idx,
            model=tool_model_name,
            resp=resp,
            request_messages=request_snapshot,
            llm_trace=llm_trace,
            ws_root=ws_root,
        )

        tool_msg = resp.choices[0].message
        tool_calls = getattr(tool_msg, "tool_calls", None) or []
        if not tool_calls:
            if round_idx == 1:
                logger.debug("repl.turn.bg no_tool_calls skip_transcript")
                return
            assistant_text = _assistant_text_from_completion_response(resp)
            assistant_msg_uuid = str(uuid.uuid4())
            _append_background_transcript_assistant(
                transcript_path,
                content=assistant_text,
                assistant_msg_uuid=assistant_msg_uuid,
                reply_to=user_msg_uuid,
            )
            elapsed_ms = int((time.perf_counter() - t0) * 1000.0)
            _append_background_log(
                ws_root,
                user_msg_uuid=user_msg_uuid,
                assistant_msg_uuid=assistant_msg_uuid,
                elapsed_ms=elapsed_ms,
                rounds=round_idx,
                tool_calls_count=total_tool_calls,
            )
            on_event(
                ToolOutputEvent(
                    workspace=ws_root,
                    user_msg_uuid=user_msg_uuid,
                    assistant_msg_uuid=assistant_msg_uuid,
                    text=assistant_text,
                    ts=utc_iso_ts(),
                    elapsed_ms=elapsed_ms,
                )
            )
            return

        total_tool_calls += len(tool_calls)
        working_messages.append(openai_assistant_message_dict(tool_msg))
        for tc in tool_calls:
            fn = tc.function
            args = fn.arguments if fn.arguments is not None else ""
            result = await execute_tool_call_fn(
                ws_root,
                fn.name,
                args,
                write_allowlist=REPL_WRITABLE_RELATIVE_PATHS,
            )
            working_messages.append(
                {"role": "tool", "tool_call_id": tc.id, "content": result}
            )

    raise RuntimeError(
        f"background tool loop exceeded max rounds: {_BG_TOOL_MAX_ROUNDS}"
    )


def start_tool_background_job(
    *,
    ws_root: Path,
    request_messages: list[dict[str, Any]],
    tool_model_name: str,
    llm_trace: bool,
    transcript_path: Path,
    user_msg_uuid: str,
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
