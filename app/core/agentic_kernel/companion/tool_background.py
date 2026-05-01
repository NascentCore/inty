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
from typing import Any, Callable, Protocol

from loguru import logger
from openai import BadRequestError

from app.services.agent_status_line import (
    clear_tool_background_db_loop,
    set_tool_background_db_loop,
)

from app.core.agentic_kernel.tools.runtime import (
    resolve_official_assistant_tool_loop_async,
)

from .llm_chat_runtime import (
    companion_turn_langsmith_parent_run_id_str,
    companion_turn_langsmith_parent_trace_id_str,
    create_chat_completion_sync,
    end_companion_turn_root_run_safe,
    langsmith_trace_id_from_completion,
    tool_path_chat_completion_kwargs,
)
from .memory_registry import get_memory_store
from .runtime_inspect_context import (
    build_last_chat_completion_request_payload,
    runtime_inspect_set_last_chat_completion_request,
    runtime_inspect_thread_overlay_begin,
    runtime_inspect_thread_overlay_end,
    tools_summary_from_openai_tools,
)
from .companion_tool_runtime import (
    REPL_WRITABLE_RELATIVE_PATHS,
    execute_tool_call,
    openai_assistant_message_dict,
    round_includes_generation_tool,
    tool_requires_client_delivery_on_success,
)
from .tool_bg_routing import (
    TOOL_BG_FIRST_ROUND_JSON_SCHEMA_NAME,
    TOOL_BG_FIRST_ROUND_RESPONSE_FORMAT,
    parse_tool_bg_first_round_skip,
    resolve_tool_bg_routing_sync,
    tool_bg_first_round_skip_schema_enabled,
)
from .utc import utc_iso_ts
from .workspace import WorkspacePaths

_OUTPUT_QUEUE: queue.Queue["ToolOutputEvent"] | None = None
_OUTPUT_QUEUE_LOCK = threading.Lock()
_ACTIVE_THREADS: set[threading.Thread] = set()
_ACTIVE_THREADS_LOCK = threading.Lock()
_ABORT_TOOL_BG_LOCK = threading.Lock()
_ABORTED_TOOL_BG_USER_MSG_UUIDS: set[str] = set()
_BG_TOOL_MAX_ROUNDS = 24


class ToolBackgroundTraceHooks(Protocol):
    """Optional REPL-side hooks for LLM round tracing (e.g. LangSmith); kernel stays import-free."""

    def on_tool_path_llm_round(
        self,
        *,
        round_idx: int,
        model: str,
        request_messages: list[dict[str, Any]],
        response: Any,
        ws_root: Path,
        trace_id: str | None,
    ) -> None: ...


def mark_tool_background_aborted(user_msg_uuid: str) -> None:
    """Foreground REPL superseded this turn: background job must not append transcript or events."""
    with _ABORT_TOOL_BG_LOCK:
        _ABORTED_TOOL_BG_USER_MSG_UUIDS.add(user_msg_uuid)


def is_tool_background_aborted(user_msg_uuid: str) -> bool:
    with _ABORT_TOOL_BG_LOCK:
        return user_msg_uuid in _ABORTED_TOOL_BG_USER_MSG_UUIDS


def clear_tool_background_abort_flag(user_msg_uuid: str) -> None:
    with _ABORT_TOOL_BG_LOCK:
        _ABORTED_TOOL_BG_USER_MSG_UUIDS.discard(user_msg_uuid)


class BackgroundToolLoopAborted(Exception):
    """User superseded REPL turn; exit background tool loop without transcript side effects."""


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


def _extract_tool_call_names(messages: list[dict[str, Any]]) -> list[str]:
    """Collect tool function names from assistant tool_call messages in order."""
    names: list[str] = []
    for m in messages:
        if m.get("role") != "assistant":
            continue
        for tc in m.get("tool_calls") or []:
            if not isinstance(tc, dict):
                continue
            fn = tc.get("function")
            if not isinstance(fn, dict):
                continue
            raw = fn.get("name")
            if isinstance(raw, str):
                n = raw.strip()
                if n:
                    names.append(n)
    return names


def _tool_bg_nl_filler_from_appended_turn(appended_messages: list[dict[str, Any]]) -> str:
    """Concatenate non-error tool string results when NL summary is empty but output_to_user is true."""
    chunks: list[str] = []
    max_chunks = 8
    max_chars = 8000
    total = 0
    for m in appended_messages:
        role = m.get("role")
        if role == "assistant":
            continue
        if role != "tool":
            continue
        tid = m.get("tool_call_id")
        if not isinstance(tid, str):
            continue
        content = m.get("content")
        if not isinstance(content, str):
            continue
        piece = content.strip()
        if not piece or piece.startswith("ERROR"):
            continue
        if len(chunks) >= max_chunks:
            break
        if total + len(piece) > max_chars:
            piece = piece[: max(0, max_chars - total - 1)] + "..."
        chunks.append(piece)
        total += len(piece)
    return "\n".join(chunks)


def _generation_tool_execution_deliver(
    appended_messages: list[dict[str, Any]],
    tool_call_names: list[str],
    image_paths: list[str],
) -> bool:
    """
    GENERATION tools must reach the client only when execution succeeded (paths or non-ERROR tool text).
    """
    if not round_includes_generation_tool(tool_call_names):
        return False
    if image_paths:
        return True
    pending: dict[str, str] = {}
    for m in appended_messages:
        if m.get("role") == "assistant":
            pending.clear()
            for tc in m.get("tool_calls") or []:
                if not isinstance(tc, dict):
                    continue
                tid = tc.get("id")
                fn = tc.get("function")
                if not isinstance(fn, dict):
                    continue
                raw_name = fn.get("name")
                if isinstance(tid, str) and isinstance(raw_name, str):
                    n = raw_name.strip()
                    if n:
                        pending[tid] = n
            continue
        if m.get("role") != "tool":
            continue
        tid = m.get("tool_call_id")
        if not isinstance(tid, str):
            continue
        name = pending.get(tid)
        if not name or not tool_requires_client_delivery_on_success(name):
            continue
        content = str(m.get("content") or "").strip()
        if content.startswith("ERROR"):
            continue
        if content:
            return True
    return False


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
    trace_id: str = ""  # run_turn turn id; links transcript rows + tool_background_done
    langsmith_trace_id: str = ""
    langsmith_run_id: str = ""
    output_to_user: bool = False
    generation_deliver: bool = False


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


def _register_thread(worker: threading.Thread) -> None:
    with _ACTIVE_THREADS_LOCK:
        _ACTIVE_THREADS.add(worker)


def _unregister_thread(worker: threading.Thread) -> None:
    with _ACTIVE_THREADS_LOCK:
        _ACTIVE_THREADS.discard(worker)


def background_tasks_count() -> int:
    with _ACTIVE_THREADS_LOCK:
        return len(_ACTIVE_THREADS)


def _assistant_text_from_completion_response(resp: Any) -> str:
    content = resp.choices[0].message.content
    if not isinstance(content, str):
        preview = repr(content)
        if len(preview) > 500:
            preview = preview[:500] + "..."
        logger.warning(
            "tool_background completion assistant message.content is not str "
            "type={} preview={}",
            type(content).__name__,
            preview,
        )
        return ""
    return content.strip()


@dataclass(frozen=True)
class _InitialToolBgCompletionMeta:
    """Winning attempt parameters for tool_background first completion (runtime_inspect)."""

    used_skip_schema: bool
    tool_choice: str | None


def _initial_tool_bg_completion_with_fallbacks(
    client: Any,
    *,
    model: str,
    messages_payload: list[dict[str, Any]],
    tools: list[Any],
    force_tools: bool,
) -> tuple[Any, _InitialToolBgCompletionMeta]:
    """
    First tool_background completion. May attach strict skip JSON schema when enabled.
    Returns (response, meta for last_chat_completion_request snapshot).
    """
    schema_on = tool_bg_first_round_skip_schema_enabled()
    schema_rf: dict[str, Any] | None = (
        TOOL_BG_FIRST_ROUND_RESPONSE_FORMAT if schema_on else None
    )
    attempts: list[tuple[dict[str, Any] | None, str | None]] = []
    if schema_rf is not None and force_tools:
        attempts.append((schema_rf, "required"))
    if schema_rf is not None:
        attempts.append((schema_rf, None))
    if force_tools:
        attempts.append((None, "required"))
    attempts.append((None, None))

    last_br: BadRequestError | None = None
    for rf, tc in attempts:
        try:
            resp = create_chat_completion_sync(
                client,
                model=model,
                messages_payload=messages_payload,
                tools=tools,
                tool_choice=tc,
                response_format=rf,
            )
            meta = _InitialToolBgCompletionMeta(
                used_skip_schema=rf is not None,
                tool_choice=tc,
            )
            return resp, meta
        except BadRequestError as exc:
            last_br = exc
            logger.warning(
                "repl.turn.bg initial_completion BadRequest response_format={} tool_choice={} err={}",
                rf is not None,
                tc,
                exc,
            )
            continue
    if last_br is not None:
        raise last_br
    raise RuntimeError("tool_background initial completion: empty attempts")


def _openai_messages_payload(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{k: v for k, v in m.items() if not k.startswith("_")} for m in messages]


def _log_bg_llm_round_result(
    *,
    round_idx: int,
    model: str,
    resp: Any,
    request_messages: list[dict[str, Any]],
    ws_root: Path,
    trace_id: str | None = None,
    trace_hooks: ToolBackgroundTraceHooks | None = None,
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
    if trace_hooks is not None:
        trace_hooks.on_tool_path_llm_round(
            round_idx=round_idx,
            model=model,
            request_messages=request_messages,
            response=resp,
            ws_root=ws_root,
            trace_id=trace_id,
        )


def _append_background_transcript_assistant(
    ws_root: Path,
    *,
    content: str,
    assistant_msg_uuid: str,
    reply_to: str,
    trace_id: str,
) -> None:
    root = ws_root.resolve()
    paths = WorkspacePaths(root=root)
    rel_tr = paths.transcript.relative_to(root).as_posix()
    get_memory_store(root).append_jsonl_record(
        rel_tr,
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
    generated_image_uris: list[str],
    trace_id: str = "",
) -> None:
    row: dict[str, Any] = {
        "kind": "tool_background_done",
        "ts": utc_iso_ts(),
        "user_msg_uuid": user_msg_uuid,
        "assistant_msg_uuid": assistant_msg_uuid,
        "elapsed_ms": elapsed_ms,
        "rounds": rounds,
        "tool_calls_count": tool_calls_count,
        "generated_image_uris": list(generated_image_uris),
    }
    if trace_id.strip():
        row["trace_id"] = trace_id
    get_memory_store(workspace_root).append_jsonl_record(
        "tool_background.jsonl",
        row,
    )


async def _run_background_tool_loop(
    *,
    ws_root: Path,
    request_messages: list[dict[str, Any]],
    tool_model_name: str,
    user_msg_uuid: str,
    trace_id: str,
    tools: list[Any],
    on_event: Callable[[ToolOutputEvent], None],
    execute_tool_call_fn: Callable[..., Any],
    client: Any,
    trace_hooks: ToolBackgroundTraceHooks | None = None,
    write_allowlist: frozenset[str] | None = None,
    repository_only_workspace_text: bool = False,
    langsmith_run_id: str = "",
) -> None:
    try:
        if is_tool_background_aborted(user_msg_uuid):
            logger.debug(
                "repl.turn.bg skip aborted before start trace_id={} user_msg_uuid={}",
                trace_id,
                user_msg_uuid,
            )
            return

        runtime_inspect_thread_overlay_begin(
            {
                "runtime_config": {
                    "source": "tool_background",
                    "tool_model_name": tool_model_name,
                    "trace_id": trace_id,
                    "tools_summary": tools_summary_from_openai_tools(tools),
                    "llm_call_notes": (
                        "Foreground CompanionLLMConfig is not copied into this async tool_background "
                        "path; use tool_model_name and last_chat_completion_request. "
                        "temperature/max_tokens are not set in companion code (provider defaults)."
                    ),
                    "openrouter_extra_body_tool_path": tool_path_chat_completion_kwargs(
                        tool_model_name
                    ),
                },
                "last_chat_completion_request": None,
            }
        )

        resolved_client = client
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
        initial_response, initial_meta = await asyncio.to_thread(
            _initial_tool_bg_completion_with_fallbacks,
            resolved_client,
            model=tool_model_name,
            messages_payload=payload,
            tools=tools,
            force_tools=force_tools,
        )
        runtime_inspect_set_last_chat_completion_request(
            build_last_chat_completion_request_payload(
                model=tool_model_name,
                messages=list(payload),
                tools=tools,
                tool_choice=initial_meta.tool_choice,
                response_format_json_schema_name=(
                    TOOL_BG_FIRST_ROUND_JSON_SCHEMA_NAME
                    if initial_meta.used_skip_schema
                    else None
                ),
            )
        )

        if is_tool_background_aborted(user_msg_uuid):
            logger.debug(
                "repl.turn.bg aborted after initial api trace_id={} user_msg_uuid={}",
                trace_id,
                user_msg_uuid,
            )
            return

        rounds_used += 1
        active_round = rounds_used
        _log_bg_llm_round_result(
            round_idx=active_round,
            model=tool_model_name,
            resp=initial_response,
            request_messages=request_snapshot,
            ws_root=ws_root,
            trace_id=trace_id,
            trace_hooks=trace_hooks,
        )

        initial_tool_calls = (
            getattr(initial_response.choices[0].message, "tool_calls", None) or []
        )
        if not initial_tool_calls:
            early_text = _assistant_text_from_completion_response(initial_response)
            if initial_meta.used_skip_schema:
                parsed = parse_tool_bg_first_round_skip(early_text)
                if parsed is not None and parsed.skip:
                    logger.debug(
                        "repl.turn.bg no_tool_calls skip_schema_true trace_id={} user_msg_uuid={}",
                        trace_id,
                        user_msg_uuid,
                    )
                elif parsed is not None and not parsed.skip:
                    logger.info(
                        "repl.turn.bg no_tool_calls skip_false_no_tools trace_id={} "
                        "user_msg_uuid={} content_chars={}",
                        trace_id,
                        user_msg_uuid,
                        len(early_text),
                    )
                else:
                    logger.info(
                        "repl.turn.bg no_tool_calls skip_json_invalid trace_id={} "
                        "user_msg_uuid={} content_chars={}",
                        trace_id,
                        user_msg_uuid,
                        len(early_text),
                    )
            elif early_text.strip():
                logger.info(
                    "repl.turn.bg no_tool_calls skip_output_queue trace_id={} "
                    "user_msg_uuid={} chars={} (foreground chat branch already shown)",
                    trace_id,
                    user_msg_uuid,
                    len(early_text),
                )
            else:
                logger.debug("repl.turn.bg no_tool_calls skip_transcript")
            return
        total_tool_calls += len(initial_tool_calls)

        allow = (
            write_allowlist
            if write_allowlist is not None
            else REPL_WRITABLE_RELATIVE_PATHS
        )

        async def execute_tool_call(
            name: str, raw_arguments: str
        ) -> tuple[str, str | None]:
            result = await execute_tool_call_fn(
                ws_root,
                name,
                raw_arguments,
                write_allowlist=allow,
                repository_only_workspace_text=repository_only_workspace_text,
            )
            return result, None

        async def continue_chat(
            messages_with_tool_results: list[dict[str, Any]],
        ) -> tuple[Any, str | None]:
            nonlocal rounds_used, active_round, total_tool_calls
            if is_tool_background_aborted(user_msg_uuid):
                raise BackgroundToolLoopAborted
            if rounds_used >= _BG_TOOL_MAX_ROUNDS:
                raise ValueError(
                    f"background tool loop exceeded max rounds: {_BG_TOOL_MAX_ROUNDS}"
                )
            rounds_used += 1
            active_round = rounds_used
            request_snapshot_inner = deepcopy(messages_with_tool_results)
            inner_payload = _openai_messages_payload(messages_with_tool_results)
            runtime_inspect_set_last_chat_completion_request(
                build_last_chat_completion_request_payload(
                    model=tool_model_name,
                    messages=list(inner_payload),
                    tools=tools,
                )
            )
            next_resp = await asyncio.to_thread(
                create_chat_completion_sync,
                resolved_client,
                model=tool_model_name,
                messages_payload=inner_payload,
                tools=tools,
            )
            _log_bg_llm_round_result(
                round_idx=active_round,
                model=tool_model_name,
                resp=next_resp,
                request_messages=request_snapshot_inner,
                ws_root=ws_root,
                trace_id=trace_id,
                trace_hooks=trace_hooks,
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
        except BackgroundToolLoopAborted:
            logger.debug(
                "repl.turn.bg aborted in tool loop trace_id={} user_msg_uuid={}",
                trace_id,
                user_msg_uuid,
            )
            return
        except ValueError as exc:
            raise RuntimeError(
                f"background tool loop exceeded max rounds: {_BG_TOOL_MAX_ROUNDS}"
            ) from exc

        if is_tool_background_aborted(user_msg_uuid):
            logger.debug(
                "repl.turn.bg aborted before append trace_id={} user_msg_uuid={}",
                trace_id,
                user_msg_uuid,
            )
            return

        raw_final = _assistant_text_from_completion_response(loop_result.response)
        bg_ls_trace = langsmith_trace_id_from_completion(loop_result.response)
        appended_turn_msgs = loop_result.messages[len(working_messages) :]
        tool_call_names = _extract_tool_call_names(appended_turn_msgs)
        image_paths = _local_paths_from_tool_messages(loop_result.messages)
        generation_deliver = _generation_tool_execution_deliver(
            appended_turn_msgs, tool_call_names, image_paths
        )
        routing = resolve_tool_bg_routing_sync(
            client=resolved_client,
            model=tool_model_name,
            create_completion_sync=create_chat_completion_sync,
            conversation_messages=list(loop_result.messages),
            final_assistant_content=raw_final,
            trace_id=trace_id,
        )
        output_to_user_flag = routing.output_to_user
        should_push = generation_deliver or output_to_user_flag
        base_nl = (routing.user_visible_text or "").strip()
        if output_to_user_flag and not base_nl:
            filler = _tool_bg_nl_filler_from_appended_turn(appended_turn_msgs)
            if filler:
                base_nl = filler
        display_text = _append_local_image_paths_for_display(base_nl, image_paths)
        elapsed_ms = int((time.perf_counter() - t0) * 1000.0)

        logger.debug(
            "repl.turn.bg policy_summary trace_id={} user_msg_uuid={} "
            "generation_deliver={} output_to_user={} should_push={} tools={} "
            "image_paths_n={} base_nl_chars={} display_chars={}",
            trace_id,
            user_msg_uuid,
            generation_deliver,
            output_to_user_flag,
            should_push,
            ",".join(tool_call_names),
            len(image_paths),
            len(base_nl),
            len(display_text),
        )

        if not should_push:
            logger.debug(
                "repl.turn.bg suppress_user_visible_output trace_id={} user_msg_uuid={} "
                "reason=should_push_false",
                trace_id,
                user_msg_uuid,
            )
            return
        if not display_text.strip() and not generation_deliver:
            logger.debug(
                "repl.turn.bg suppress_user_visible_output empty_display trace_id={} "
                "user_msg_uuid={} generation_deliver={} output_to_user={} tools={}",
                trace_id,
                user_msg_uuid,
                generation_deliver,
                output_to_user_flag,
                ",".join(tool_call_names),
            )
            return
        if not display_text.strip() and generation_deliver:
            display_text = _append_local_image_paths_for_display("", image_paths)
        if is_tool_background_aborted(user_msg_uuid):
            logger.debug(
                "repl.turn.bg aborted before transcript append trace_id={} user_msg_uuid={}",
                trace_id,
                user_msg_uuid,
            )
            return
        assistant_msg_uuid = str(uuid.uuid4())
        _append_background_transcript_assistant(
            ws_root,
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
            generated_image_uris=image_paths,
            trace_id=trace_id,
        )
        logger.debug(
            "repl.turn.bg deliver trace_id={} user_msg_uuid={} assistant_msg_uuid={} "
            "generation_deliver={} output_to_user={} display_chars={} image_paths_n={}",
            trace_id,
            user_msg_uuid,
            assistant_msg_uuid,
            generation_deliver,
            output_to_user_flag,
            len(display_text),
            len(image_paths),
        )
        on_event(
            ToolOutputEvent(
                workspace=ws_root,
                user_msg_uuid=user_msg_uuid,
                assistant_msg_uuid=assistant_msg_uuid,
                text=display_text,
                ts=utc_iso_ts(),
                elapsed_ms=elapsed_ms,
                trace_id=trace_id,
                langsmith_trace_id=bg_ls_trace,
                langsmith_run_id=langsmith_run_id,
                output_to_user=output_to_user_flag,
                generation_deliver=generation_deliver,
            )
        )
    finally:
        runtime_inspect_thread_overlay_end()
        clear_tool_background_abort_flag(user_msg_uuid)


def start_tool_background_job(
    *,
    ws_root: Path,
    request_messages: list[dict[str, Any]],
    tool_model_name: str,
    user_msg_uuid: str,
    trace_id: str,
    tools: list[Any],
    on_event: Callable[[ToolOutputEvent], None] | None = None,
    execute_tool_call_fn: Callable[..., Any] = execute_tool_call,
    client: Any,
    trace_hooks: ToolBackgroundTraceHooks | None = None,
    write_allowlist: frozenset[str] | None = None,
    repository_only_workspace_text: bool = False,
    main_event_loop: asyncio.AbstractEventLoop | None = None,
    langsmith_parent_run: Any | None = None,
) -> None:
    def _effective_on_event(ev: ToolOutputEvent) -> None:
        if on_event is not None:
            on_event(ev)
        else:
            push_output_event(ev)

    def _runner() -> None:
        # Register here with current_thread(), not the Thread instance from threading.Thread(...).
        # Unit tests patch threading.Thread with MagicMock; pre-start register would leak mocks.
        _register_thread(threading.current_thread())
        bg_ls_err: str | None = None

        bg_ls_run_id = companion_turn_langsmith_parent_run_id_str(langsmith_parent_run)

        def _run_async_tool_loop() -> None:
            asyncio.run(
                _run_background_tool_loop(
                    ws_root=ws_root,
                    request_messages=request_messages,
                    tool_model_name=tool_model_name,
                    user_msg_uuid=user_msg_uuid,
                    trace_id=trace_id,
                    tools=tools,
                    on_event=_effective_on_event,
                    execute_tool_call_fn=execute_tool_call_fn,
                    client=client,
                    trace_hooks=trace_hooks,
                    write_allowlist=write_allowlist,
                    repository_only_workspace_text=repository_only_workspace_text,
                    langsmith_run_id=bg_ls_run_id,
                )
            )

        try:
            try:
                if main_event_loop is not None:
                    set_tool_background_db_loop(main_event_loop)
                if langsmith_parent_run is not None:
                    from langsmith.run_helpers import set_tracing_parent

                    with set_tracing_parent(langsmith_parent_run):
                        _run_async_tool_loop()
                else:
                    _run_async_tool_loop()
            except BaseException as exc:
                bg_ls_err = repr(exc)
                logger.exception("repl.turn.bg job failed")
            finally:
                end_companion_turn_root_run_safe(
                    langsmith_parent_run,
                    error=bg_ls_err,
                    ls_end_source="tool_background_thread",
                )
                clear_tool_background_db_loop()
        finally:
            _unregister_thread(threading.current_thread())

    t = threading.Thread(target=_runner, name="inty-v2-tool-bg", daemon=False)
    logger.info(
        "langsmith_companion_parent_run tool_bg_thread_start inty_trace_id={} "
        "user_msg_uuid={} ls_trace_id={} thread_name={} daemon={}",
        trace_id,
        user_msg_uuid,
        companion_turn_langsmith_parent_trace_id_str(langsmith_parent_run),
        t.name,
        t.daemon,
    )
    t.start()
