"""Companion turn executor: 单轮对话的完整执行流程。

可选 ``tool_bg_idle_event``：在加载 transcript 之前等待上一轮异步 tool_background 线程收尾，
保证主 ``transcript.jsonl``（或维护内在节拍用的 ``transcript_inner_tick.jsonl``）已含工具摘要后再组装本轮 chat/tool messages。

**Importance scoring (significance perception)**：When the foreground chat call uses
``response_format=DUAL_LLM_CHAT_RESPONSE_FORMAT``, the assistant JSON envelope includes three
1-10 scores and ``output_to_user`` beside ``user_facing_reply``. Parsed scores go to ``significance_meta`` and are
stored on the assistant transcript row and returned on ``CompanionTurnResult.significance_perception``
(API layer may mirror into ``chat_history.meta_data``). Eligibility: foreground envelope applies to
async dual-LLM (tools present) always for that chat leg; for the single-completion branch only when
``use_dual_structured_chat`` is true (no tools, not inner-tick async background route). If the parsed
envelope has ``output_to_user=false`` on either foreground chat path, ``run_turn`` logs WARNING with
``trace_id``: the prompt/schema contract requires true on chat branches (false is for tool_background
routing); the model may still drift. Full pipeline notes: ``significance_perception.py`` module docstring.

**``output_to_user`` warning**: The dual-LLM JSON envelope is shared with ``tool_background`` finish,
where ``output_to_user`` may be false (silent recap). On **foreground** chat completions it must be
true. If the model returns false anyway (schema allows any boolean; prompts say true here), we log
``run_turn ... output_to_user=false (expected true for chat branch)`` so traces can flag
prompt/model confusion, not a parser bug.
"""

from __future__ import annotations

import asyncio
import contextvars
import os
import threading
import time
import uuid
from contextlib import nullcontext
from copy import deepcopy
from typing import Any

from loguru import logger

from app.schemas.implicit_signals import ImplicitSignalBundle
from app.utils.config import CompanionMemoryBootstrapType
from app.core.companion_harness.llm.langsmith_invocation_extra import (
    SOURCE_FOREGROUND_DUAL_LLM_ENVELOPE,
    invocation_extra,
)

from .llm_client import (
    LLM_SCENE_CHAT,
    LLM_SCENE_INNER_TICK,
    CompanionLLMClient,
)
from .llm_runtime_events import (
    LlmRuntimeEventBind,
    companion_llm_runtime_event_bind_ctx,
    record_llm_inference_failure,
)
from .memory_pipeline import (
    MemoryPipelineConfig,
    memory_update_after_turn,
    schedule_memory_update_after_turn,
)
from .memory_store import MemoryStore
from .models import (
    CompanionTurnResult,
    ContextMeta,
    InnerTickMode,
    PromptBundle,
    transcript_relative_path_for_turn_persistence,
)
from .prompt_stack import companion_turn_tools_and_system_messages
from .significance_perception import (
    DUAL_LLM_CHAT_RESPONSE_FORMAT,
    split_dual_llm_chat_branch_message,
)
from .transcript_compaction import CompactionConfig as TranscriptCompactionConfig
from .turn_pipeline import (
    build_companion_turn_prompt_plan,
    load_companion_turn_state,
    resolve_turn_runtime_flags,
)
from .tool_background import (
    ToolOutputEvent,
    push_output_event,
    start_tool_background_job,
)
from .turn_routes import BackgroundToolEventSink, TurnRouteMode
from .companion_tool_runtime import (
    MEMORY_STORE_READ_DOCUMENT_MAX_CHARS_CAP,
    execute_tool_call as repl_execute_tool_call,
)
from .runtime_inspect_context import (
    build_last_chat_completion_request_payload,
    build_turn_runtime_config_dict,
    runtime_inspect_begin_turn,
    runtime_inspect_end_turn,
    runtime_inspect_set_correlation,
    runtime_inspect_set_last_chat_completion_request,
    runtime_inspect_set_runtime_config,
    runtime_inspect_set_scoped_memory_store,
)
from .tools import WRITABLE_RELATIVE_PATHS
from .utc import utc_iso_ts
from .implicit_signal_messages import (
    MEMORY_DIARY_USER_LINE_FOR_IMPLICIT_SIGN_ON,
    USER_SIGNED_ON_TRIGGER_USER_TEXT,
)
from .llm_chat_runtime import (
    companion_turn_langsmith_parent_trace_id_str,
    create_companion_turn_root_run,
    end_companion_turn_root_run_safe,
    langsmith_llm_run_id_from_completion,
    langsmith_trace_id_from_completion,
)
from .memory_store_scope import DEFAULT_MEMORY_STORE_SCOPE_PATHS

CHAT_TRACK_RESPONSE_MESSAGE_TITLE = "## Response from the chat track"


def _replace_leading_system_messages_multi(
    messages: list[dict[str, Any]], system_messages: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Strip initial system role block(s) and prepend structured system messages."""
    i = 0
    while i < len(messages) and messages[i].get("role") == "system":
        i += 1
    return [*system_messages, *messages[i:]]


def _async_dual_llm_system_message_variants(
    *,
    store: MemoryStore,
    bundle: PromptBundle,
    context: ContextMeta,
    memory_bootstrap_type: str,
    inner_tick_turn: bool,
    route_inner_mode: InnerTickMode,
    implicit_signal_bundle: ImplicitSignalBundle | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Compact tool-path stack vs full chat-path stack; shares inner_tick routing with refresh/tool_bg.

    Implicit sign-on (internal ``implicit_user_signed_on_turn``) rounds strip tools in the main ``run_turn`` prefix pass
    (``implicit_user_signed_on_turn``), so routing is chat-only sync, not this async dual branch.
    We intentionally omit that flag here (equivalent to ``False``): this helper only runs when
    ``TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL`` already won, i.e. tool-backed rounds
    where the model should not reuse the sign-on ``chat_only`` contract (greeting turns skip tool
    loops entirely, like a brief hello to someone familiar).
    """
    _, tool_system_msgs, _ = companion_turn_tools_and_system_messages(
        store=store,
        bundle=bundle,
        context=context,
        memory_bootstrap_type=memory_bootstrap_type,
        inner_tick_turn=inner_tick_turn,
        inner_tick_mode=route_inner_mode,
        tool_side_compact_system_prompt=True,
        include_significance_perception_slice=False,
        implicit_signal_bundle=implicit_signal_bundle,
        implicit_user_signed_on_turn=False,
    )
    _, chat_system_msgs, _ = companion_turn_tools_and_system_messages(
        store=store,
        bundle=bundle,
        context=context,
        memory_bootstrap_type=memory_bootstrap_type,
        inner_tick_turn=inner_tick_turn,
        inner_tick_mode=route_inner_mode,
        tool_side_compact_system_prompt=False,
        include_significance_perception_slice=True,
        implicit_signal_bundle=implicit_signal_bundle,
        implicit_user_signed_on_turn=False,
    )
    return tool_system_msgs, chat_system_msgs


def _preview(s: str, max_len: int = 280) -> str:
    one = s.replace("\n", " ").strip()
    if len(one) <= max_len:
        return one
    return one[: max_len - 1] + "..."


async def _await_tool_background_idle_if_configured(
    tool_bg_idle_event: threading.Event | None,
    *,
    idle_wait_timeout_sec: float,
    scope_registry_key: str,
) -> None:
    if tool_bg_idle_event is None:
        return

    def _wait() -> bool:
        return tool_bg_idle_event.wait(timeout=idle_wait_timeout_sec)

    ok = await asyncio.to_thread(_wait)
    if not ok:
        logger.warning(
            "run_turn tool_bg_idle wait timed out after {:.2f}s scope={}",
            idle_wait_timeout_sec,
            scope_registry_key,
        )


async def run_turn(
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
    repository_only_store_text: bool = False,
    memory_bootstrap_type: str = CompanionMemoryBootstrapType.NONE.value,
    background_output_sink: BackgroundToolEventSink | None = None,
    preset_user_msg_uuid: str | None = None,
    implicit_signal_bundle: ImplicitSignalBundle | None = None,
    langsmith_parent_run_enabled: bool | None = None,
    tool_bg_idle_event: threading.Event | None = None,
) -> CompanionTurnResult:
    """
    执行一轮完整对话。

    - 加载 context + prompt bundle + transcript
    - 组装 system prompt + messages
    - 调用 LLM（有工具时：对 ``TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL``，普通用户轮先 await
      前台 JSON envelope chat，再将 ``user_facing_reply`` 注入工具路径后 dispatch ``tool_background``；
      **维护性 inner tick**（``inner_tick_turn`` 且非 proactive）在该路由下**始终**跳过前台 envelope，
      直接 ``start_tool_background_job``（``force_tools_first_round=True``））。
    - 持久化 transcript
    - 调度记忆管线

    返回 ``CompanionTurnResult``（``assistant_text`` 与可选 ``significance_perception``）。
    """
    t0 = time.perf_counter()
    paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    mem_cfg = memory_config or MemoryPipelineConfig()

    runtime_flags = resolve_turn_runtime_flags(
        user_text=user_text,
        inner_tick_turn=inner_tick_turn,
        inner_tick_mode=inner_tick_mode,
        implicit_signal_bundle=implicit_signal_bundle,
    )
    user_text = runtime_flags.effective_user_text
    tick_proactive = runtime_flags.tick_proactive
    route_inner_mode = runtime_flags.route_inner_mode
    implicit_sign_on_turn = runtime_flags.implicit_sign_on_turn

    logger.info(
        "run_turn start scope={} user_chars={} inner_tick_turn={} inner_tick_mode={} defer_memory={}",
        store.scope.registry_key(),
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

    raw_idle_timeout = (
        os.environ.get("INTY_TOOL_BG_IDLE_WAIT_TIMEOUT_SEC", "").strip() or ""
    )
    try:
        idle_wait_timeout_sec = (
            float(raw_idle_timeout)
            if raw_idle_timeout
            else float(llm_client.config.async_chat_front_timeout_sec)
        )
    except ValueError:
        idle_wait_timeout_sec = float(llm_client.config.async_chat_front_timeout_sec)
    await _await_tool_background_idle_if_configured(
        tool_bg_idle_event,
        idle_wait_timeout_sec=idle_wait_timeout_sec,
        scope_registry_key=store.scope.registry_key(),
    )

    loaded_state = load_companion_turn_state(
        store=store,
        inner_tick_turn=inner_tick_turn,
        route_inner_mode=route_inner_mode,
        transcript_llm_window_max_messages=transcript_llm_window_max_messages,
    )
    context = loaded_state.context
    bundle = loaded_state.bundle
    prompt_plan = build_companion_turn_prompt_plan(
        store=store,
        loaded_state=loaded_state,
        user_text=user_text,
        memory_bootstrap_type=memory_bootstrap_type,
        inner_tick_turn=inner_tick_turn,
        route_inner_mode=route_inner_mode,
        tick_proactive=tick_proactive,
        implicit_signal_bundle=implicit_signal_bundle,
        implicit_sign_on_turn=implicit_sign_on_turn,
        transcript_compaction=transcript_compaction,
    )
    tools_for_turn = prompt_plan.tools_for_turn
    route_mode = prompt_plan.route_mode
    messages = prompt_plan.messages
    use_dual_structured_chat = prompt_plan.use_dual_structured_chat
    user_msg_uuid = preset_user_msg_uuid if preset_user_msg_uuid else str(uuid.uuid4())

    ts_user = utc_iso_ts()
    trace_id = str(uuid.uuid4())
    langsmith_trace_acc = ""
    langsmith_llm_run_acc = ""

    last_text = ""
    significance_meta: dict[str, Any] | None = None
    reply_modality: str = "text"
    voice_message_script = ""
    tool_background_started = False
    t_loop = time.perf_counter()

    inspect_token = runtime_inspect_begin_turn()
    llm_runtime_bind_token: contextvars.Token[LlmRuntimeEventBind | None] | None = None
    try:
        _llm_ev_phase = "inner_tick" if inner_tick_turn else "foreground_chat"
        llm_runtime_bind_token = companion_llm_runtime_event_bind_ctx.set(
            LlmRuntimeEventBind(
                memory_store=store,
                trace_id=trace_id,
                user_msg_uuid=user_msg_uuid,
                phase=_llm_ev_phase,
                scene=None,
            )
        )
        runtime_inspect_set_scoped_memory_store(store)
        runtime_inspect_set_runtime_config(
            build_turn_runtime_config_dict(
                llm_client=llm_client,
                mem_cfg=mem_cfg,
                context=context,
                transcript_llm_window_max_messages=loaded_state.window_cap,
                inner_tick_turn=inner_tick_turn,
                inner_tick_mode=route_inner_mode,
                repository_only_store_text=repository_only_store_text,
                transcript_compaction=transcript_compaction,
                memory_store_read_document_max_chars_cap=(
                    MEMORY_STORE_READ_DOCUMENT_MAX_CHARS_CAP
                ),
            )
        )
        runtime_inspect_set_correlation(
            {"trace_id": trace_id, "user_msg_uuid": user_msg_uuid}
        )

        langsmith_parent_run = create_companion_turn_root_run(
            inty_trace_id=trace_id,
            user_msg_uuid=user_msg_uuid,
            chat_model=llm_client.resolve_model("chat"),
            tool_model=llm_client.resolve_model("tool"),
            user_id=context.user_id,
            companion_id=context.companion_id,
            parent_run_enabled=langsmith_parent_run_enabled,
            inner_tick_turn=inner_tick_turn,
            inner_tick_mode=route_inner_mode if inner_tick_turn else None,
            implicit_user_signed_on=implicit_sign_on_turn,
        )
        _ls_tid = companion_turn_langsmith_parent_trace_id_str(langsmith_parent_run)
        if _ls_tid:
            langsmith_trace_acc = _ls_tid
        if langsmith_parent_run is not None:
            logger.debug(
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
                    tool_system_msgs, chat_system_msgs = (
                        _async_dual_llm_system_message_variants(
                            store=store,
                            bundle=bundle,
                            context=context,
                            memory_bootstrap_type=memory_bootstrap_type,
                            inner_tick_turn=inner_tick_turn,
                            route_inner_mode=route_inner_mode,
                            implicit_signal_bundle=implicit_signal_bundle,
                        )
                    )
                    chat_msgs = _replace_leading_system_messages_multi(
                        messages, chat_system_msgs
                    )
                    tool_msgs = _replace_leading_system_messages_multi(
                        messages, tool_system_msgs
                    )
                    chat_model = llm_client.resolve_model("chat")
                    tool_model = llm_client.resolve_model("tool")
                    foreground_scene = (
                        LLM_SCENE_INNER_TICK
                        if inner_tick_turn and not tick_proactive
                        else LLM_SCENE_CHAT
                    )

                    def _kernel_bg_on_event(ev: ToolOutputEvent) -> None:
                        if background_output_sink is not None:
                            background_output_sink(ev)
                        else:
                            push_output_event(ev)

                    skip_foreground_envelope = inner_tick_turn and not tick_proactive
                    if skip_foreground_envelope:
                        logger.info(
                            "run_turn inner_tick skip foreground envelope "
                            "inner_tick_mode={} model_chat={}",
                            inner_tick_mode.value,
                            chat_model,
                        )
                        last_text = ""
                        significance_meta = None
                        reply_modality = "text"
                        voice_message_script = ""
                        tool_msgs_for_bg = deepcopy(tool_msgs)
                        force_tools_first_round = True
                    else:
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
                                    scene=foreground_scene,
                                    langsmith_extra=invocation_extra(
                                        source=SOURCE_FOREGROUND_DUAL_LLM_ENVELOPE,
                                    ),
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
                            record_llm_inference_failure(
                                model=chat_model,
                                exc=exc,
                                foreground_timeout_sec=llm_client.config.async_chat_front_timeout_sec,
                            )
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
                            foreground_scene,
                        )
                        msg = resp.choices[0].message
                        _dual_split = split_dual_llm_chat_branch_message(msg)
                        last_text = _dual_split.visible_text
                        significance_meta = _dual_split.significance_meta
                        fg_output_to_user = _dual_split.output_to_user
                        reply_modality = _dual_split.reply_modality
                        voice_message_script = _dual_split.voice_message_script
                        # Async foreground chat leg (tools present): same dual-LLM envelope contract as
                        # single-shot structured chat; ``output_to_user`` must be true here. False is for
                        # tool_background routing only; non-fatal drift -> WARNING with ``trace_id``.
                        if fg_output_to_user is False:
                            logger.warning(
                                "run_turn foreground dual_llm envelope output_to_user=false "
                                "trace_id={} (expected true for chat branch)",
                                trace_id,
                            )
                        fg_text = last_text.strip()
                        tool_msgs_for_bg = deepcopy(tool_msgs)
                        if fg_text:
                            tool_msgs_for_bg.append(
                                {
                                    "role": "assistant",
                                    "content": (
                                        f"{CHAT_TRACK_RESPONSE_MESSAGE_TITLE}\n\n{fg_text}"
                                    ),
                                }
                            )
                        force_tools_first_round = not bool(fg_text)
                    start_tool_background_job(
                        memory_store=store,
                        request_messages=tool_msgs_for_bg,
                        tool_model_name=tool_model,
                        user_msg_uuid=user_msg_uuid,
                        trace_id=trace_id,
                        tools=tools_for_turn,
                        on_event=_kernel_bg_on_event,
                        execute_tool_call_fn=repl_execute_tool_call,
                        client=llm_client.sync_client_for_route("tool"),
                        chat_completions_sync=llm_client.chat_completions_sync,
                        write_allowlist=WRITABLE_RELATIVE_PATHS,
                        repository_only_store_text=repository_only_store_text,
                        main_event_loop=asyncio.get_running_loop(),
                        langsmith_parent_run=langsmith_parent_run,
                        memory_bootstrap_type=memory_bootstrap_type,
                        inner_tick_turn=inner_tick_turn,
                        inner_tick_mode=route_inner_mode,
                        implicit_signal_bundle=implicit_signal_bundle,
                        tool_bg_idle_event=tool_bg_idle_event,
                        force_tools_first_round=force_tools_first_round,
                    )
                    tool_background_started = True
                    logger.info(
                        "run_turn loop_done rounds={} loop_total_ms={:.0f} route={}",
                        1,
                        (time.perf_counter() - t_loop) * 1000.0,
                        route_mode.value,
                    )
                    logger.debug(
                        "langsmith_companion_parent_run run_turn_fg_done inty_trace_id={} "
                        "user_msg_uuid={} ls_trace_id={} defer_parent_end_to_tool_bg_thread=1",
                        trace_id,
                        user_msg_uuid,
                        companion_turn_langsmith_parent_trace_id_str(
                            langsmith_parent_run
                        ),
                    )
                else:
                    t_api = time.perf_counter()
                    resolved_model = llm_client.resolve_model("chat")
                    logger.debug(
                        "run_turn llm_request model={} route={} (no tools; single completion)",
                        resolved_model,
                        route_mode.value,
                    )
                    runtime_inspect_set_last_chat_completion_request(
                        build_last_chat_completion_request_payload(
                            model=resolved_model,
                            messages=messages,
                            tools=None,
                        )
                    )
                    llm_scene = (
                        LLM_SCENE_INNER_TICK
                        if inner_tick_turn and not tick_proactive
                        else LLM_SCENE_CHAT
                    )
                    resp = llm_client.chat_completion(
                        messages=messages,
                        model=resolved_model,
                        tools=None,
                        response_format=(
                            DUAL_LLM_CHAT_RESPONSE_FORMAT
                            if use_dual_structured_chat
                            else None
                        ),
                        scene=llm_scene,
                    )
                    langsmith_trace_acc = (
                        langsmith_trace_id_from_completion(resp) or langsmith_trace_acc
                    )
                    ls_lr = langsmith_llm_run_id_from_completion(resp)
                    if ls_lr:
                        langsmith_llm_run_acc = ls_lr
                    approx_ctx_chars = sum(
                        len(str(m.get("content") or "")) for m in messages
                    )
                    logger.info(
                        "run_turn llm_round={} model={} chat_completions_ms={:.0f} "
                        "approx_ctx_chars={} route={} inner_tick_proactive_chat={}",
                        1,
                        resolved_model,
                        (time.perf_counter() - t_api) * 1000.0,
                        approx_ctx_chars,
                        route_mode.value,
                        tick_proactive,
                    )
                    msg = resp.choices[0].message
                    if use_dual_structured_chat:
                        _dual_split = split_dual_llm_chat_branch_message(msg)
                        last_text = _dual_split.visible_text
                        significance_meta = _dual_split.significance_meta
                        fg_output_to_user = _dual_split.output_to_user
                        reply_modality = _dual_split.reply_modality
                        voice_message_script = _dual_split.voice_message_script
                        # Single-shot path: one completion, no tool loop, structured dual-LLM envelope.
                        # Contract (see ``prompts/system_messages._dual_llm_chat_structured_output_contract_text``):
                        # ``output_to_user`` must be true on foreground chat; false is for tool_background
                        # finish envelopes only. Non-fatal model drift; WARNING ties to ``trace_id``.
                        if fg_output_to_user is False:
                            logger.warning(
                                "run_turn single_shot dual_llm envelope output_to_user=false "
                                "trace_id={} (expected true for chat branch)",
                                trace_id,
                            )
                    else:
                        raw_content = msg.content or ""
                        last_text = raw_content.strip()
                        reply_modality = "text"
                        voice_message_script = ""
                    logger.info(
                        "run_turn loop_done single_shot route={} loop_total_ms={:.0f}",
                        route_mode.value,
                        (time.perf_counter() - t_loop) * 1000.0,
                    )
            except BaseException as exc:
                if tool_background_started and isinstance(exc, Exception):
                    try:
                        exc.companion_tool_background_started = True
                    except Exception:
                        pass
                if not tool_background_started:
                    end_companion_turn_root_run_safe(
                        langsmith_parent_run,
                        error=repr(exc),
                        ls_end_source="run_turn_sync_exc",
                    )
                else:
                    logger.debug(
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
                if not tool_background_started:
                    end_companion_turn_root_run_safe(
                        langsmith_parent_run, ls_end_source="run_turn_sync_ok"
                    )
                else:
                    logger.debug(
                        "langsmith_companion_parent_run run_turn_exit_skip_main_end "
                        "inty_trace_id={} user_msg_uuid={} ls_trace_id={}",
                        trace_id,
                        user_msg_uuid,
                        companion_turn_langsmith_parent_trace_id_str(
                            langsmith_parent_run
                        ),
                    )
    finally:
        if llm_runtime_bind_token is not None:
            companion_llm_runtime_event_bind_ctx.reset(llm_runtime_bind_token)
        runtime_inspect_end_turn(inspect_token)

    # 持久化 transcript
    rel_tr = (
        paths.transcript
        if implicit_sign_on_turn
        else transcript_relative_path_for_turn_persistence(
            inner_tick_turn=inner_tick_turn,
            inner_tick_mode=route_inner_mode,
        )
    )
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
    if reply_modality == "voice_message":
        assistant_row["reply_modality"] = reply_modality
        if voice_message_script:
            assistant_row["voice_message_script"] = voice_message_script
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
            store,
            user_text=memory_user_text,
            assistant_text=last_text,
            complete_fn=_complete_fn,
            config=mem_cfg,
        )
    else:
        _mem_sync_tok = companion_llm_runtime_event_bind_ctx.set(
            LlmRuntimeEventBind(
                memory_store=store,
                trace_id=trace_id,
                user_msg_uuid=user_msg_uuid,
                phase="memory_pipeline",
                scene=None,
            )
        )
        try:

            def _complete_fn_sync(msgs: list[dict[str, Any]], model_role: str) -> str:
                return llm_client.complete_text(msgs, model_role=model_role)

            memory_update_after_turn(
                store,
                user_text=memory_user_text,
                assistant_text=last_text,
                complete_fn=_complete_fn_sync,
                config=mem_cfg,
            )
        finally:
            companion_llm_runtime_event_bind_ctx.reset(_mem_sync_tok)

    logger.info(
        "run_turn done assistant_chars={} ms={:.0f} inty_trace_id={} user_msg_uuid={} "
        "langsmith_trace_id={} langsmith_run_id={}",
        len(last_text),
        (time.perf_counter() - t0) * 1000.0,
        trace_id,
        user_msg_uuid,
        langsmith_trace_acc or "",
        langsmith_llm_run_acc or "",
    )
    return CompanionTurnResult(
        assistant_text=last_text,
        reply_modality=reply_modality,  # type: ignore[arg-type]
        voice_message_script=voice_message_script,
        significance_perception=significance_meta,
        user_msg_uuid=user_msg_uuid,
        assistant_msg_uuid=assistant_msg_uuid,
        trace_id=trace_id,
        langsmith_trace_id=langsmith_trace_acc,
        langsmith_run_id=langsmith_llm_run_acc,
        tool_background_started=tool_background_started,
        assistant_source="inner_tick" if inner_tick_turn else "chat",
        turn_start_context_mode=context.context_mode,
    )
