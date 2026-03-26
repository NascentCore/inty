"""Text Turn Orchestrator：唯一将助手回复写入 transcript.jsonl 的入口。"""

from __future__ import annotations

import asyncio
import time
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any

from loguru import logger

from .client import (
    chat_model,
    default_model,
    dual_llm_enabled,
    get_client,
    tool_model,
)
from .file_store import append_jsonl, read_text
from .memory_update import memory_update_after_turn, schedule_memory_update_after_turn
from .models import (
    TRANSCRIPT_WINDOW_MAX_MESSAGES,
    ChatMessage,
    ContextMeta,
    PromptBundle,
    load_context_meta,
    load_prompt_bundle,
    load_transcript,
    transcript_for_llm_turn,
)
from .paths import WorkspacePaths
from .prompts import build_system_prompt
from .utc import local_date_str, utc_iso_ts
from .llm_trace import (
    TRANSCRIPT_MSG_UUID_KEY,
    emit_trace,
    summarize_completion_response,
    summarize_messages,
)
from .fal_z_image_tool import _reset_fal_async_client_after_short_lived_loop
from .heartbeat_schedule import HEARTBEAT_SYNTHETIC_USER_TEXT
from .workspace_init_tools import (
    REPL_WRITABLE_RELATIVE_PATHS,
    build_openai_repl_tools,
    execute_tool_call,
    openai_assistant_message_dict,
)

_REPL_USER_PROFILE_TOOL_MAX_ROUNDS = 24


def _payload_chars_for_debug(messages: list[dict[str, Any]]) -> int:
    """Rough size of what goes to the API (content + tool argument strings)."""
    total = 0
    for m in messages:
        c = m.get("content")
        if isinstance(c, str):
            total += len(c)
        for tc in m.get("tool_calls") or []:
            if isinstance(tc, dict):
                fn = tc.get("function") or {}
                a = fn.get("arguments")
                if isinstance(a, str):
                    total += len(a)
    return total


def _preview_for_debug(s: str, max_len: int = 280) -> str:
    one = s.replace("\n", " ").strip()
    if len(one) <= max_len:
        return one
    return one[: max_len - 1] + "…"


def _debug_log_prompt_bundle(bundle: PromptBundle, *, context: ContextMeta) -> None:
    intimate = context.context_mode.strip().lower() == "intimate"
    logger.debug(
        "run_turn.context mode={} user_id={} companion_id={} chat_id={} intimate={}",
        context.context_mode,
        context.user_id,
        context.companion_id,
        context.chat_id,
        intimate,
    )
    logger.debug(
        "run_turn.bundle_chars identity={} soul={} user={} memory={} "
        "agents={} tools={} heartbeat={} diary_today={} day_summary={}",
        len(bundle.identity),
        len(bundle.soul),
        len(bundle.user_md),
        len(bundle.memory_md),
        len(bundle.agents_md),
        len(bundle.tools_md),
        len(bundle.heartbeat_md),
        len(bundle.memory_raw_diary_today_md),
        len(bundle.memory_day_summary_today_md),
    )


def _openai_messages_payload(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop underscore-prefixed keys (e.g. transcript uuid) before chat.completions."""
    return [{k: v for k, v in m.items() if not k.startswith("_")} for m in messages]


def _chat_completion_create(
    client: Any,
    *,
    model: str,
    messages_payload: list[dict[str, Any]],
    tools: list[Any],
) -> Any:
    create_kw: dict[str, Any] = {
        "model": model,
        "messages": deepcopy(messages_payload),
    }
    if tools:
        create_kw["tools"] = tools
        create_kw["parallel_tool_calls"] = True
    return client.chat.completions.create(**create_kw)


def _assistant_text_from_completion_response(resp: Any) -> str:
    msg = resp.choices[0].message
    content = msg.content
    if not isinstance(content, str):
        return ""
    return content.strip()


def _merge_visible_assistant_text(chat_text: str, tool_text: str) -> str:
    chat_s = chat_text.strip()
    tool_s = tool_text.strip()
    if not chat_s and not tool_s:
        return ""
    if not chat_s:
        return tool_s
    if not tool_s:
        return chat_s
    if chat_s == tool_s:
        return chat_s
    if chat_s in tool_s:
        return tool_s
    if tool_s in chat_s:
        return chat_s
    return chat_s + "\n\n" + tool_s


def _log_llm_round_result(
    *,
    round_idx: int,
    model: str,
    resp: Any,
    messages: list[dict[str, Any]],
    llm_trace: bool,
    llm_trace_where: str,
    root: Path,
) -> None:
    ch0 = resp.choices[0]
    fr = getattr(ch0, "finish_reason", None) or "?"
    msg = ch0.message
    tcs_pre = getattr(msg, "tool_calls", None) or []
    u = getattr(resp, "usage", None)
    tok = ""
    if u is not None:
        pt = getattr(u, "prompt_tokens", None)
        ct = getattr(u, "completion_tokens", None)
        tt = getattr(u, "total_tokens", None)
        if pt is not None and ct is not None:
            tok = f" prompt={pt} completion={ct}"
            if tt is not None:
                tok += f" total={tt}"
    logger.info(
        "repl.turn llm_round={} finish_reason={} tool_calls_n={} model={}",
        round_idx,
        fr,
        len(tcs_pre),
        model,
    )
    logger.debug(
        "repl.turn llm_round={} finish_reason={} tool_calls={} payload_msgs={} "
        "payload_chars={}{}",
        round_idx,
        fr,
        len(tcs_pre),
        len(_openai_messages_payload(messages)),
        _payload_chars_for_debug(messages),
        tok,
    )
    if llm_trace:
        emit_trace(
            llm_trace_where,
            round_idx=round_idx,
            model=model,
            messages=summarize_messages(
                messages,
                ws_label=root.name,
                trace_day=local_date_str(),
            ),
            response=summarize_completion_response(resp),
        )


async def _run_turn_with_user_profile_tools(
    messages: list[dict[str, Any]],
    root: Path,
    *,
    llm_trace: bool = True,
    heartbeat_turn: bool = False,
) -> str:
    """chat.completions + user_profile_record，直到模型不再调用工具。"""
    client = get_client()
    model = default_model()
    dual_enabled = dual_llm_enabled()
    chat_route_model = chat_model()
    tool_route_model = tool_model()
    tools: list[Any] = [] if heartbeat_turn else build_openai_repl_tools()
    if not heartbeat_turn and not tools:
        raise RuntimeError("build_openai_repl_tools() returned empty list")
    if heartbeat_turn and dual_enabled:
        logger.debug("repl.turn dual_llm disabled for heartbeat turn")
    last_text = ""
    t_loop = time.perf_counter()
    for round_idx in range(1, _REPL_USER_PROFILE_TOOL_MAX_ROUNDS + 1):
        if dual_enabled and not heartbeat_turn:
            logger.debug(
                "repl.turn llm_round={} dual_llm=true chat_model={} tool_model={} "
                "shared_context_msgs={}",
                round_idx,
                chat_route_model,
                tool_route_model,
                len(messages),
            )
            base_payload = _openai_messages_payload(messages)
            request_messages = deepcopy(messages)

            async def _run_chat_branch() -> Any:
                t_api_chat = time.perf_counter()
                resp_chat = await asyncio.to_thread(
                    _chat_completion_create,
                    client,
                    model=chat_route_model,
                    messages_payload=base_payload,
                    tools=[],
                )
                logger.info(
                    "repl.turn llm_round={} branch=chat chat_completions_ms={:.0f} model={}",
                    round_idx,
                    (time.perf_counter() - t_api_chat) * 1000.0,
                    chat_route_model,
                )
                return resp_chat

            async def _run_tool_branch() -> Any:
                t_api_tool = time.perf_counter()
                resp_tool = await asyncio.to_thread(
                    _chat_completion_create,
                    client,
                    model=tool_route_model,
                    messages_payload=base_payload,
                    tools=tools,
                )
                logger.info(
                    "repl.turn llm_round={} branch=tool chat_completions_ms={:.0f} model={}",
                    round_idx,
                    (time.perf_counter() - t_api_tool) * 1000.0,
                    tool_route_model,
                )
                return resp_tool

            chat_task = asyncio.create_task(_run_chat_branch())
            tool_task = asyncio.create_task(_run_tool_branch())
            pending_map: dict[asyncio.Task[Any], str] = {
                chat_task: "chat",
                tool_task: "tool",
            }
            done_results: dict[str, Any] = {}
            try:
                while pending_map:
                    done_set, _ = await asyncio.wait(
                        pending_map.keys(),
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    for finished_task in done_set:
                        branch = pending_map.pop(finished_task)
                        resp_any = await finished_task
                        done_results[branch] = resp_any
                        _log_llm_round_result(
                            round_idx=round_idx,
                            model=chat_route_model
                            if branch == "chat"
                            else tool_route_model,
                            resp=resp_any,
                            messages=request_messages,
                            llm_trace=llm_trace,
                            llm_trace_where="repl.turn.dual.chat"
                            if branch == "chat"
                            else "repl.turn.dual.tool",
                            root=root,
                        )
                        msg_branch = resp_any.choices[0].message
                        messages.append(openai_assistant_message_dict(msg_branch))
            except BaseException:
                for still_pending in pending_map:
                    still_pending.cancel()
                raise
            chat_resp = done_results["chat"]
            tool_resp = done_results["tool"]
            chat_text = _assistant_text_from_completion_response(chat_resp)
            tool_text = _assistant_text_from_completion_response(tool_resp)
            last_text = _merge_visible_assistant_text(chat_text, tool_text)
            tool_msg = tool_resp.choices[0].message
            tool_calls = getattr(tool_msg, "tool_calls", None) or []
            if not tool_calls:
                break
        else:
            t_api = time.perf_counter()
            resp = _chat_completion_create(
                client,
                model=model,
                messages_payload=_openai_messages_payload(messages),
                tools=tools,
            )
            logger.info(
                "repl.turn llm_round={} branch=single chat_completions_ms={:.0f} model={}",
                round_idx,
                (time.perf_counter() - t_api) * 1000.0,
                model,
            )
            msg = resp.choices[0].message
            _log_llm_round_result(
                round_idx=round_idx,
                model=model,
                resp=resp,
                messages=messages,
                llm_trace=llm_trace,
                llm_trace_where="repl.turn",
                root=root,
            )
            tool_calls = getattr(msg, "tool_calls", None) or []
            messages.append(openai_assistant_message_dict(msg))
            if not tool_calls:
                last_text = _assistant_text_from_completion_response(resp)
                break
        propose = ",".join(
            getattr(getattr(tc, "function", None), "name", "?") for tc in tool_calls
        )
        logger.info(
            "repl.turn llm_round={} executing_tools=[{}] tool_call_ids={}",
            round_idx,
            propose,
            ",".join((getattr(tc, "id", "") or "")[:12] for tc in tool_calls),
        )
        for tc in tool_calls:
            fn = tc.function
            name = fn.name
            args = fn.arguments if fn.arguments is not None else ""
            logger.info(
                "repl.turn tool_call round={} name={} tool_call_id={} arg_bytes={}",
                round_idx,
                name,
                (getattr(tc, "id", None) or "")[:16],
                len(args.encode("utf-8")),
            )
            logger.debug(
                "repl.turn tool_call_detail round={} name={} args_preview={}",
                round_idx,
                name,
                _preview_for_debug(args),
            )
            t_tool = time.perf_counter()
            result = await execute_tool_call(
                root,
                name,
                args,
                write_allowlist=REPL_WRITABLE_RELATIVE_PATHS,
            )
            ok = not result.startswith("ERROR:")
            logger.info(
                "repl.turn tool_done round={} name={} execute_ms={:.0f} "
                "result_chars={} ok={} preview={}",
                round_idx,
                name,
                (time.perf_counter() - t_tool) * 1000.0,
                len(result),
                ok,
                _preview_for_debug(result, max_len=260),
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
            )
    else:
        raise RuntimeError(
            f"repl user_profile tool loop exceeded max_rounds={_REPL_USER_PROFILE_TOOL_MAX_ROUNDS}"
        )
    logger.info(
        "repl.turn loop_done rounds={} loop_total_ms={:.0f}",
        round_idx,
        (time.perf_counter() - t_loop) * 1000.0,
    )
    return last_text


def _required_workspace_file_paths(paths: WorkspacePaths) -> tuple[Path, ...]:
    return (
        paths.identity,
        paths.soul,
        paths.user_md,
        paths.memory_md,
        paths.transcript,
    )


def is_workspace_initialized(workspace: Path) -> bool:
    """与 run_turn 相同：五件套存在则认为已初始化。"""
    paths = WorkspacePaths(root=workspace.resolve())
    for p in _required_workspace_file_paths(paths):
        if not p.is_file():
            return False
    return True


# IDENTITY/USER 仍像模板或未约定时的子串（与 bootstrap 桩、示例工作区一致；用于启动时是否先开口）
_IDENTITY_STUB_MARKERS: tuple[str, ...] = (
    "（在此填写",
    "还没定",
    "等你来",
    "待对话填充",
)
_USER_STUB_MARKERS: tuple[str, ...] = (
    "（在此填写",
    "等待你告诉",
    "等待观察",
    "待对话填充",
)


def _transcript_is_empty(paths: WorkspacePaths) -> bool:
    if not paths.transcript.is_file():
        return True
    return len(load_transcript(paths.transcript)) == 0


def _text_matches_any_marker(text: str, markers: tuple[str, ...]) -> bool:
    s = text.strip()
    if not s:
        return True
    return any(m in s for m in markers)


def needs_startup_profile_inquiry(workspace: Path) -> bool:
    """
    已初始化、且 transcript 仍为空时：若 IDENTITY 或 USER 仍像占位/未约定，
    则 REPL 启动时应由助手先开口发问（见 main.repl）。
    """
    root = workspace.resolve()
    if not is_workspace_initialized(root):
        return False
    paths = WorkspacePaths(root=root)
    if not _transcript_is_empty(paths):
        return False
    ident = read_text(paths.identity) if paths.identity.is_file() else ""
    user_md = read_text(paths.user_md) if paths.user_md.is_file() else ""
    id_stub = _text_matches_any_marker(ident, _IDENTITY_STUB_MARKERS)
    user_stub = _text_matches_any_marker(user_md, _USER_STUB_MARKERS)
    out = id_stub or user_stub
    logger.debug(
        "needs_startup_profile_inquiry ws={} id_stub={} user_stub={} -> {}",
        root.name,
        id_stub,
        user_stub,
        out,
    )
    return out


def _require_workspace_files(paths: WorkspacePaths) -> None:
    for p in _required_workspace_file_paths(paths):
        if not p.is_file():
            raise ValueError(f"missing required workspace file: {p}")


async def run_turn(
    workspace: Path,
    user_text: str,
    *,
    heartbeat_turn: bool = False,
    debug_print_system: bool = False,
    defer_memory_update: bool = True,
    llm_trace: bool = False,
) -> str:
    """defer_memory_update=True：记忆管线入队后台跑，先返回助手文本（repl 先打印）；False：单轮 CLI 退出前跑完。
    heartbeat_turn=True：用户侧为系统合成的陪伴心跳提示，不跑记忆管线。"""
    t0 = time.perf_counter()
    root = workspace.resolve()
    paths = WorkspacePaths(root=root)
    if heartbeat_turn:
        user_text = HEARTBEAT_SYNTHETIC_USER_TEXT

    logger.info(
        "run_turn start path={} user_chars={} heartbeat_turn={} defer_memory={} llm_trace={}",
        root,
        len(user_text),
        heartbeat_turn,
        defer_memory_update,
        llm_trace,
    )
    try:
        _require_workspace_files(paths)
        get_client()

        t_load = time.perf_counter()
        context = load_context_meta(paths.context_json)
        bundle = load_prompt_bundle(paths, meta=context)
        loaded = load_transcript(paths.transcript)
        transcript = transcript_for_llm_turn(loaded)
        _debug_log_prompt_bundle(bundle, context=context)

        system = build_system_prompt(
            bundle,
            context,
            enable_user_profile_tool=True,
            heartbeat_turn=heartbeat_turn,
        )
        logger.debug(
            "run_turn system_prompt_chars={} sep_count={}",
            len(system),
            system.count("\n\n---\n\n"),
        )
        logger.info(
            "run_turn load_context_build_system_ms={:.0f} transcript_msgs={} transcript_window=last_{}",
            (time.perf_counter() - t_load) * 1000.0,
            len(transcript),
            TRANSCRIPT_WINDOW_MAX_MESSAGES,
        )
        if debug_print_system:
            print(system)
            print("=" * 80)

        messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
        for m in transcript:
            row: dict[str, Any] = {"role": m.role, "content": m.content}
            if m.uuid:
                row[TRANSCRIPT_MSG_UUID_KEY] = m.uuid
            messages.append(row)

        user_msg_uuid = str(uuid.uuid4())
        messages.append(
            {
                "role": "user",
                "content": user_text,
                TRANSCRIPT_MSG_UUID_KEY: user_msg_uuid,
            }
        )

        logger.debug(
            "run_turn llm_input messages_count={} payload_chars={} user_msg_uuid={} "
            "user_preview={}",
            len(messages),
            _payload_chars_for_debug(messages),
            user_msg_uuid,
            _preview_for_debug(user_text, max_len=200),
        )

        # Must snapshot user time before the LLM call; assistant time is taken after (below).
        ts_user = utc_iso_ts()
        t_main = time.perf_counter()
        assistant_text = await _run_turn_with_user_profile_tools(
            messages,
            root,
            llm_trace=llm_trace,
            heartbeat_turn=heartbeat_turn,
        )
        logger.info(
            "run_turn main_repl_tool_loop_wall_ms={:.0f}",
            (time.perf_counter() - t_main) * 1000.0,
        )

        assistant_msg_uuid = str(uuid.uuid4())
        t_persist = time.perf_counter()
        user_row: dict[str, Any] = {
            "role": "user",
            "content": user_text,
            "ts": ts_user,
            "uuid": user_msg_uuid,
        }
        if heartbeat_turn:
            user_row["heartbeat"] = True
        append_jsonl(paths.transcript, user_row)
        ts_asst = utc_iso_ts()
        append_jsonl(
            paths.transcript,
            {
                "role": "assistant",
                "content": assistant_text,
                "ts": ts_asst,
                "uuid": assistant_msg_uuid,
            },
        )

        logger.info(
            "run_turn persist_transcript_ms={:.0f}",
            (time.perf_counter() - t_persist) * 1000.0,
        )

        if heartbeat_turn:
            logger.debug(
                "run_turn memory_pipeline=skipped (heartbeat_turn) user_uuid={} assistant_uuid={}",
                user_msg_uuid,
                assistant_msg_uuid,
            )
        elif defer_memory_update:
            logger.debug(
                "run_turn memory_pipeline=async (enqueue) user_uuid={} assistant_uuid={}",
                user_msg_uuid,
                assistant_msg_uuid,
            )
            schedule_memory_update_after_turn(
                paths,
                user_text=user_text,
                assistant_text=assistant_text,
                llm_trace=llm_trace,
            )
        else:
            logger.debug(
                "run_turn memory_pipeline=sync (blocking) user_uuid={} assistant_uuid={}",
                user_msg_uuid,
                assistant_msg_uuid,
            )
            memory_update_after_turn(
                paths,
                user_text=user_text,
                assistant_text=assistant_text,
                llm_trace=llm_trace,
            )

        logger.info(
            "run_turn done assistant_chars={} ms={:.0f}",
            len(assistant_text),
            (time.perf_counter() - t0) * 1000.0,
        )
        logger.debug(
            "run_turn assistant_preview={}",
            _preview_for_debug(assistant_text, max_len=400),
        )
        return assistant_text
    finally:
        await _reset_fal_async_client_after_short_lived_loop()
