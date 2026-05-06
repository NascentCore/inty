"""Companion turn executor: 单轮对话的完整执行流程。"""

from __future__ import annotations

import asyncio
import time
import uuid
from contextlib import nullcontext
from copy import deepcopy
from pathlib import Path
from typing import Any

from loguru import logger

from app.schemas.implicit_signals import ImplicitSignalBundle
from app.utils.config import CompanionWorkspaceBootstrapType

from .llm_client import (
    LLM_SCENE_CHAT,
    LLM_SCENE_INNER_TICK,
    LLM_SCENE_TOOL_CALL,
    CompanionLLMClient,
)
from .message_format import openai_assistant_message_dict
from .memory_pipeline import (
    MemoryPipelineConfig,
    memory_update_after_turn,
    schedule_memory_update_after_turn,
)
from .memory_store import MemoryStore
from .models import (
    INNER_TICK_SYNTHETIC_USER_TEXT,
    TRANSCRIPT_WINDOW_MAX_MESSAGES,
    ChatMessage,
    CompanionTurnResult,
    InnerTickMode,
    load_context_meta,
    load_prompt_bundle,
    load_transcript_from_store,
    transcript_for_llm_turn,
)
from .transcript_compaction import (
    CompactionConfig as TranscriptCompactionConfig,
    ConversationCompactor,
    load_compaction_state_from_store,
    save_compaction_state_to_store,
    transcript_rows_to_openai_dialogue,
)
from .prompt_stack import (
    companion_turn_tools_and_system_messages,
    refresh_companion_turn_prompt_stack,
)
from .significance_perception import (
    DUAL_LLM_CHAT_RESPONSE_FORMAT,
    split_dual_llm_chat_branch_content,
)
from .tool_background import (
    ToolOutputEvent,
    push_output_event,
    start_tool_background_job,
)
from .turn_routes import BackgroundToolEventSink, TurnRouteMode
from .companion_tool_runtime import (
    WORKSPACE_READ_FILE_MAX_CHARS_CAP,
    execute_tool_call as repl_execute_tool_call,
)
from .runtime_inspect_context import (
    build_last_chat_completion_request_payload,
    build_turn_runtime_config_dict,
    runtime_inspect_begin_turn,
    runtime_inspect_end_turn,
    runtime_inspect_set_last_chat_completion_request,
    runtime_inspect_set_runtime_config,
)
from .tools import WRITABLE_RELATIVE_PATHS
from .utc import utc_iso_ts
from .heartbeat import (
    HEARTBEAT_SYNTHETIC_USER_TEXT,
    PROACTIVE_HEARTBEAT_TRANSCRIPT_USER_MARKER,
)
from .implicit_signal_messages import (
    MEMORY_DIARY_USER_LINE_FOR_IMPLICIT_SIGN_ON,
    USER_SIGNED_ON_TRIGGER_USER_TEXT,
    implicit_user_signed_on_chat_turn,
)
from .llm_chat_runtime import (
    companion_turn_langsmith_parent_trace_id_str,
    create_companion_turn_root_run,
    end_companion_turn_root_run_safe,
    langsmith_llm_run_id_from_completion,
    langsmith_trace_id_from_completion,
)
from .workspace import WorkspacePaths

_MAX_TOOL_ROUNDS = 24


def _replace_leading_system_messages_multi(
    messages: list[dict[str, Any]], system_messages: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Strip initial system role block(s) and prepend structured system messages."""
    i = 0
    while i < len(messages) and messages[i].get("role") == "system":
        i += 1
    return [*system_messages, *messages[i:]]


def _preview(s: str, max_len: int = 280) -> str:
    one = s.replace("\n", " ").strip()
    if len(one) <= max_len:
        return one
    return one[: max_len - 1] + "..."


async def run_turn(
    workspace: Path,
    user_text: str,
    *,
    store: MemoryStore,
    llm_client: CompanionLLMClient,
    inner_tick_turn: bool = False,
    inner_tick_mode: InnerTickMode = InnerTickMode.MAINTENANCE,
    defer_memory_update: bool = True,
    memory_config: MemoryPipelineConfig | None = None,
    transcript_compaction: TranscriptCompactionConfig | None = None,
    transcript_llm_window_max_messages: int | None = None,
    repository_only_workspace_text: bool = False,
    workspace_bootstrap_type: str = CompanionWorkspaceBootstrapType.NONE.value,
    background_output_sink: BackgroundToolEventSink | None = None,
    preset_user_msg_uuid: str | None = None,
    implicit_signal_bundle: ImplicitSignalBundle | None = None,
    langsmith_parent_run_enabled: bool | None = None,
) -> CompanionTurnResult:
    """
    执行一轮完整对话。

    - 加载 context + prompt bundle + transcript
    - 组装 system prompt + messages
    - 调用 LLM (带 tool loop)
    - 持久化 transcript
    - 调度记忆管线

    返回 ``CompanionTurnResult``（``assistant_text`` 与可选 ``significance_perception``）。
    """
    t0 = time.perf_counter()
    root = workspace.resolve()
    paths = WorkspacePaths(root=root)
    mem_cfg = memory_config or MemoryPipelineConfig()

    tick_proactive = inner_tick_turn and inner_tick_mode == InnerTickMode.PROACTIVE_CHAT
    route_inner_mode = inner_tick_mode if inner_tick_turn else InnerTickMode.MAINTENANCE
    implicit_sign_on_turn = implicit_user_signed_on_chat_turn(
        implicit_signal_bundle=implicit_signal_bundle,
        inner_tick_turn=inner_tick_turn,
    )

    if inner_tick_turn:
        user_text = (
            PROACTIVE_HEARTBEAT_TRANSCRIPT_USER_MARKER
            if tick_proactive
            else INNER_TICK_SYNTHETIC_USER_TEXT
        )

    logger.info(
        "run_turn start path={} user_chars={} inner_tick_turn={} inner_tick_mode={} defer_memory={}",
        root,
        len(user_text),
        inner_tick_turn,
        inner_tick_mode.value if inner_tick_turn else "-",
        defer_memory_update,
    )
    logger.debug(
        "run_turn llm_client api_base={} model_chat={} model_tool={} dual_llm=True",
        llm_client.config.api_base,
        llm_client.resolve_model("chat"),
        llm_client.resolve_model("tool"),
    )

    # 加载 context 与 prompt bundle
    context = load_context_meta(paths.context_json, store=store)
    bundle = load_prompt_bundle(paths, store, meta=context)
    rel_tr = paths.transcript.relative_to(root).as_posix()
    loaded = load_transcript_from_store(store, rel_tr)
    window_cap = transcript_llm_window_max_messages
    if window_cap is None:
        window_cap = TRANSCRIPT_WINDOW_MAX_MESSAGES
    transcript = transcript_for_llm_turn(loaded, max_messages=window_cap)

    tools_for_turn, system_messages, route_mode = (
        companion_turn_tools_and_system_messages(
            workspace_root=root,
            bundle=bundle,
            context=context,
            workspace_bootstrap_type=workspace_bootstrap_type,
            inner_tick_turn=inner_tick_turn,
            inner_tick_mode=inner_tick_mode,
            enable_async_tool_background=llm_client.config.enable_async_tool_background,
            tool_side_compact_system_prompt=False,
            include_significance_perception_slice=None,
            implicit_signal_bundle=implicit_signal_bundle,
            implicit_user_signed_on_turn=implicit_sign_on_turn,
        )
    )
    use_dual_structured_chat = (
        (not inner_tick_turn)
        and (not tools_for_turn)
        and route_mode != TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL
    )

    prior_user_turns = sum(1 for m in loaded if m.role == "user")
    compaction_turn_idx = prior_user_turns + 1

    if transcript_compaction is not None and not inner_tick_turn:
        rel_compact = paths.context_compaction_state_json.relative_to(root).as_posix()
        prior_state = load_compaction_state_from_store(store, rel_compact)
        compactor = ConversationCompactor(
            transcript_compaction,
            initial_state=prior_state,
        )
        pre_user: list[dict[str, Any]] = [
            *system_messages,
            *transcript_rows_to_openai_dialogue(transcript),
        ]
        outcome = compactor.maybe_compact(messages=pre_user, turn=compaction_turn_idx)
        messages = list(outcome.messages)
        if outcome.did_compact:
            save_compaction_state_to_store(store, rel_compact, outcome.state)
            logger.info(
                "run_turn transcript_compaction did_compact=true reason={} before={} after={}",
                outcome.reason,
                outcome.approx_chars_before,
                outcome.approx_chars_after,
            )
    else:
        messages = list(system_messages)
        for m in transcript:
            messages.append({"role": m.role, "content": m.content})
    user_msg_uuid = preset_user_msg_uuid if preset_user_msg_uuid else str(uuid.uuid4())
    if tick_proactive:
        messages.append({"role": "system", "content": HEARTBEAT_SYNTHETIC_USER_TEXT})
    if implicit_sign_on_turn:
        # Tail user (not system): same copy as trailing system caused repetitive greetings.
        messages.append({"role": "user", "content": USER_SIGNED_ON_TRIGGER_USER_TEXT})
    else:
        messages.append({"role": "user", "content": user_text})

    ts_user = utc_iso_ts()
    trace_id = str(uuid.uuid4())
    langsmith_trace_acc = ""
    langsmith_llm_run_acc = ""

    # Tool loop
    tools = tools_for_turn
    last_text = ""
    significance_meta: dict[str, Any] | None = None
    used_async_tool_background = False
    t_loop = time.perf_counter()

    inspect_token = runtime_inspect_begin_turn()
    try:
        runtime_inspect_set_runtime_config(
            build_turn_runtime_config_dict(
                llm_client=llm_client,
                mem_cfg=mem_cfg,
                context=context,
                transcript_llm_window_max_messages=window_cap,
                inner_tick_turn=inner_tick_turn,
                inner_tick_mode=route_inner_mode,
                repository_only_workspace_text=repository_only_workspace_text,
                transcript_compaction=transcript_compaction,
                workspace_read_file_max_chars_cap=WORKSPACE_READ_FILE_MAX_CHARS_CAP,
            )
        )

        langsmith_parent_run = create_companion_turn_root_run(
            inty_trace_id=trace_id,
            user_msg_uuid=user_msg_uuid,
            chat_model=llm_client.resolve_model("chat"),
            tool_model=llm_client.resolve_model("tool"),
            user_id=context.user_id,
            companion_id=context.companion_id,
            parent_run_enabled=langsmith_parent_run_enabled,
        )
        _ls_tid = companion_turn_langsmith_parent_trace_id_str(langsmith_parent_run)
        if _ls_tid:
            langsmith_trace_acc = _ls_tid
        if langsmith_parent_run is not None:
            logger.info(
                "langsmith_companion_parent_run run_turn_bind inty_trace_id={} "
                "user_msg_uuid={} ls_trace_id={} route_mode={} defer_end_to_bg={}",
                trace_id,
                user_msg_uuid,
                _ls_tid,
                route_mode.value,
                route_mode == TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL,
            )

        _langsmith_cm = nullcontext()
        if langsmith_parent_run is not None:
            from langsmith.run_helpers import tracing_context

            _langsmith_cm = tracing_context(parent=langsmith_parent_run)

        with _langsmith_cm:
            try:
                if route_mode == TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL:
                    used_async_tool_background = True
                    _, tool_system_msgs, _ = companion_turn_tools_and_system_messages(
                        workspace_root=root,
                        bundle=bundle,
                        context=context,
                        workspace_bootstrap_type=workspace_bootstrap_type,
                        inner_tick_turn=False,
                        inner_tick_mode=InnerTickMode.MAINTENANCE,
                        enable_async_tool_background=(
                            llm_client.config.enable_async_tool_background
                        ),
                        tool_side_compact_system_prompt=True,
                        include_significance_perception_slice=False,
                        implicit_signal_bundle=implicit_signal_bundle,
                    )
                    _, chat_system_msgs, _ = companion_turn_tools_and_system_messages(
                        workspace_root=root,
                        bundle=bundle,
                        context=context,
                        workspace_bootstrap_type=workspace_bootstrap_type,
                        inner_tick_turn=False,
                        inner_tick_mode=InnerTickMode.MAINTENANCE,
                        enable_async_tool_background=(
                            llm_client.config.enable_async_tool_background
                        ),
                        tool_side_compact_system_prompt=False,
                        include_significance_perception_slice=True,
                        implicit_signal_bundle=implicit_signal_bundle,
                    )
                    chat_msgs = _replace_leading_system_messages_multi(
                        messages, chat_system_msgs
                    )
                    tool_msgs = _replace_leading_system_messages_multi(
                        messages, tool_system_msgs
                    )
                    chat_model = llm_client.resolve_model("chat")
                    tool_model = llm_client.resolve_model("tool")

                    def _kernel_bg_on_event(ev: ToolOutputEvent) -> None:
                        if background_output_sink is not None:
                            background_output_sink(ev)
                        else:
                            push_output_event(ev)

                    start_tool_background_job(
                        ws_root=root,
                        request_messages=deepcopy(tool_msgs),
                        tool_model_name=tool_model,
                        user_msg_uuid=user_msg_uuid,
                        trace_id=trace_id,
                        tools=tools_for_turn,
                        on_event=_kernel_bg_on_event,
                        execute_tool_call_fn=repl_execute_tool_call,
                        client=llm_client.sync_client_for_route("tool"),
                        chat_completions_sync=llm_client.chat_completions_sync,
                        write_allowlist=WRITABLE_RELATIVE_PATHS,
                        repository_only_workspace_text=repository_only_workspace_text,
                        main_event_loop=asyncio.get_running_loop(),
                        langsmith_parent_run=langsmith_parent_run,
                        workspace_bootstrap_type=workspace_bootstrap_type,
                        enable_async_tool_background=(
                            llm_client.config.enable_async_tool_background
                        ),
                    )

                    runtime_inspect_set_last_chat_completion_request(
                        build_last_chat_completion_request_payload(
                            model=chat_model,
                            messages=chat_msgs,
                            tools=None,
                        )
                    )
                    t_api = time.perf_counter()
                    try:

                        def _chat_sync() -> Any:
                            return llm_client.chat_completion(
                                messages=chat_msgs,
                                model=chat_model,
                                tools=None,
                                response_format=DUAL_LLM_CHAT_RESPONSE_FORMAT,
                                scene=LLM_SCENE_CHAT,
                            )

                        resp = await asyncio.wait_for(
                            asyncio.to_thread(_chat_sync),
                            timeout=llm_client.config.async_chat_front_timeout_sec,
                        )
                        langsmith_trace_acc = (
                            langsmith_trace_id_from_completion(resp)
                            or langsmith_trace_acc
                        )
                        ls_lr = langsmith_llm_run_id_from_completion(resp)
                        if ls_lr:
                            langsmith_llm_run_acc = ls_lr
                    except asyncio.TimeoutError as exc:
                        raise RuntimeError(
                            f"async chat front timed out after "
                            f"{llm_client.config.async_chat_front_timeout_sec:.0f}s "
                            f"(trace_id={trace_id})"
                        ) from exc

                    approx_ctx_chars = sum(
                        len(str(m.get("content") or "")) for m in chat_msgs
                    )
                    logger.info(
                        "run_turn llm_round={} model={} chat_completions_ms={:.0f} "
                        "approx_ctx_chars={} async_chat_tool_background "
                        "foreground_chat scene={}",
                        1,
                        chat_model,
                        (time.perf_counter() - t_api) * 1000.0,
                        approx_ctx_chars,
                        LLM_SCENE_CHAT,
                    )
                    msg = resp.choices[0].message
                    # TODO(companion-dual-envelope-reasoning-channel): If ``msg.content`` is empty
                    # but the model filled ``reasoning`` / ``reasoning_details``, dual envelope parse
                    # yields empty assistant text and API returns 500. See
                    # ``app/core/agentic_kernel/llm/chat_completions.py`` (TODO tag).
                    raw_content = msg.content or ""
                    last_text, significance_meta = split_dual_llm_chat_branch_content(
                        raw_content
                    )
                    logger.info(
                        "run_turn loop_done rounds={} loop_total_ms={:.0f} route={}",
                        1,
                        (time.perf_counter() - t_loop) * 1000.0,
                        route_mode.value,
                    )
                    logger.info(
                        "langsmith_companion_parent_run run_turn_fg_done inty_trace_id={} "
                        "user_msg_uuid={} ls_trace_id={} defer_parent_end_to_tool_bg_thread=1",
                        trace_id,
                        user_msg_uuid,
                        companion_turn_langsmith_parent_trace_id_str(
                            langsmith_parent_run
                        ),
                    )
                else:
                    for round_idx in range(1, _MAX_TOOL_ROUNDS + 1):
                        t_api = time.perf_counter()
                        resolved_model = llm_client.resolve_model(
                            "tool" if tools else "chat"
                        )
                        logger.debug(
                            "run_turn llm_request round={} model={} tools_enabled={}",
                            round_idx,
                            resolved_model,
                            bool(tools),
                        )
                        runtime_inspect_set_last_chat_completion_request(
                            build_last_chat_completion_request_payload(
                                model=resolved_model,
                                messages=messages,
                                tools=tools or None,
                            )
                        )
                        llm_scene = (
                            LLM_SCENE_INNER_TICK
                            if inner_tick_turn and not tick_proactive
                            else (LLM_SCENE_TOOL_CALL if tools else LLM_SCENE_CHAT)
                        )
                        resp = llm_client.chat_completion(
                            messages=messages,
                            model=resolved_model,
                            tools=tools or None,
                            response_format=(
                                DUAL_LLM_CHAT_RESPONSE_FORMAT
                                if use_dual_structured_chat
                                else None
                            ),
                            scene=llm_scene,
                        )
                        langsmith_trace_acc = (
                            langsmith_trace_id_from_completion(resp)
                            or langsmith_trace_acc
                        )
                        ls_lr = langsmith_llm_run_id_from_completion(resp)
                        if ls_lr:
                            langsmith_llm_run_acc = ls_lr
                        approx_ctx_chars = sum(
                            len(str(m.get("content") or "")) for m in messages
                        )
                        logger.info(
                            "run_turn llm_round={} model={} chat_completions_ms={:.0f} "
                            "approx_ctx_chars={} tools={} inner_tick_proactive_chat={}",
                            round_idx,
                            resolved_model,
                            (time.perf_counter() - t_api) * 1000.0,
                            approx_ctx_chars,
                            len(tools or []),
                            tick_proactive,
                        )

                        msg = resp.choices[0].message
                        tool_calls = getattr(msg, "tool_calls", None) or []
                        messages.append(openai_assistant_message_dict(msg))

                        if not tool_calls:
                            # TODO(companion-dual-envelope-reasoning-channel): Same as async foreground
                            # branch above when ``msg.content`` is null; grep tag for full note.
                            raw_content = msg.content or ""
                            if use_dual_structured_chat:
                                last_text, significance_meta = (
                                    split_dual_llm_chat_branch_content(raw_content)
                                )
                            else:
                                last_text = raw_content.strip()
                            break

                        for tc in tool_calls:
                            fn = tc.function
                            name = fn.name
                            args = fn.arguments if fn.arguments is not None else ""
                            logger.info(
                                "run_turn tool_call round={} name={} trace_id={}",
                                round_idx,
                                name,
                                trace_id,
                            )
                            result = await repl_execute_tool_call(
                                root,
                                name,
                                args,
                                write_allowlist=WRITABLE_RELATIVE_PATHS,
                                repository_only_workspace_text=repository_only_workspace_text,
                            )
                            logger.info(
                                "run_turn tool_done round={} name={} result_chars={} ok={}",
                                round_idx,
                                name,
                                len(result),
                                not result.startswith("ERROR:"),
                            )
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tc.id,
                                    "content": result,
                                }
                            )
                        tools_for_turn = refresh_companion_turn_prompt_stack(
                            workspace=root,
                            store=store,
                            workspace_bootstrap_type=workspace_bootstrap_type,
                            inner_tick_turn=inner_tick_turn,
                            inner_tick_mode=inner_tick_mode,
                            enable_async_tool_background=(
                                llm_client.config.enable_async_tool_background
                            ),
                            messages=messages,
                            tool_side_compact_system_prompt=False,
                            implicit_signal_bundle=implicit_signal_bundle,
                        )
                        tools = tools_for_turn
                    else:
                        raise RuntimeError(
                            f"tool loop exceeded max_rounds={_MAX_TOOL_ROUNDS}"
                        )

                    logger.info(
                        "run_turn loop_done rounds={} loop_total_ms={:.0f}",
                        round_idx,
                        (time.perf_counter() - t_loop) * 1000.0,
                    )
            except BaseException as exc:
                if not used_async_tool_background:
                    end_companion_turn_root_run_safe(
                        langsmith_parent_run,
                        error=repr(exc),
                        ls_end_source="run_turn_sync_exc",
                    )
                else:
                    logger.info(
                        "langsmith_companion_parent_run run_turn_exc_skip_main_end "
                        "inty_trace_id={} user_msg_uuid={} ls_trace_id={} exc_type={}",
                        trace_id,
                        user_msg_uuid,
                        companion_turn_langsmith_parent_trace_id_str(
                            langsmith_parent_run
                        ),
                        type(exc).__name__,
                    )
                raise
            else:
                if not used_async_tool_background:
                    end_companion_turn_root_run_safe(
                        langsmith_parent_run, ls_end_source="run_turn_sync_ok"
                    )
                else:
                    logger.info(
                        "langsmith_companion_parent_run run_turn_exit_skip_main_end "
                        "inty_trace_id={} user_msg_uuid={} ls_trace_id={}",
                        trace_id,
                        user_msg_uuid,
                        companion_turn_langsmith_parent_trace_id_str(
                            langsmith_parent_run
                        ),
                    )
    finally:
        runtime_inspect_end_turn(inspect_token)

    # 持久化 transcript
    assistant_msg_uuid = str(uuid.uuid4())
    if implicit_sign_on_turn:
        sign_on_row: dict[str, Any] = {
            "role": "user",
            "content": USER_SIGNED_ON_TRIGGER_USER_TEXT,
            "ts": ts_user,
            "uuid": user_msg_uuid,
            "trace_id": trace_id,
            "implicit_user_signed_on": True,
        }
        store.append_jsonl_record(rel_tr, sign_on_row)
    else:
        user_row: dict[str, Any] = {
            "role": "user",
            "content": user_text,
            "ts": ts_user,
            "uuid": user_msg_uuid,
        }
        if inner_tick_turn:
            user_row["inner_tick"] = True
        if tick_proactive:
            user_row["heartbeat"] = True
        user_row["trace_id"] = trace_id
        store.append_jsonl_record(rel_tr, user_row)
    memory_user_text = (
        MEMORY_DIARY_USER_LINE_FOR_IMPLICIT_SIGN_ON
        if implicit_sign_on_turn
        else user_text
    )
    assistant_row: dict[str, Any] = {
        "role": "assistant",
        "content": last_text,
        "ts": utc_iso_ts(),
        "uuid": assistant_msg_uuid,
        "reply_to": user_msg_uuid,
        "source": "inner_tick" if inner_tick_turn else "chat",
        "trace_id": trace_id,
    }
    if significance_meta:
        assistant_row["significance_perception"] = significance_meta
    store.append_jsonl_record(rel_tr, assistant_row)

    # 记忆管线
    if inner_tick_turn:
        logger.debug(
            "run_turn memory_pipeline=skipped (inner_tick_turn) mode={}",
            inner_tick_mode.value,
        )
    elif defer_memory_update:

        def _complete_fn(msgs: list[dict[str, Any]], model_role: str) -> str:
            return llm_client.complete_text(msgs, model_role=model_role)

        schedule_memory_update_after_turn(
            paths,
            store=store,
            user_text=memory_user_text,
            assistant_text=last_text,
            complete_fn=_complete_fn,
            config=mem_cfg,
        )
    else:

        def _complete_fn_sync(msgs: list[dict[str, Any]], model_role: str) -> str:
            return llm_client.complete_text(msgs, model_role=model_role)

        memory_update_after_turn(
            paths,
            store=store,
            user_text=memory_user_text,
            assistant_text=last_text,
            complete_fn=_complete_fn_sync,
            config=mem_cfg,
        )

    logger.info(
        "run_turn done assistant_chars={} ms={:.0f}",
        len(last_text),
        (time.perf_counter() - t0) * 1000.0,
    )
    return CompanionTurnResult(
        assistant_text=last_text,
        significance_perception=significance_meta,
        user_msg_uuid=user_msg_uuid,
        trace_id=trace_id,
        langsmith_trace_id=langsmith_trace_acc,
        langsmith_run_id=langsmith_llm_run_acc,
        used_async_tool_background=used_async_tool_background,
        assistant_source="inner_tick" if inner_tick_turn else "chat",
    )
