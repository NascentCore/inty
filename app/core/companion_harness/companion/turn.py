"""Companion turn executor: 单轮对话的完整执行流程。

Memory-phase invariant **AwakeTurn**: see ``companion.turn_invariants`` — this module
only appends transcript JSONL on ``MemoryStore``; batch curation belongs in **DreamingBatch**.

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
routing); the model may still drift. Full pipeline notes: ``dual_llm_chat_branch_envelope`` module docstring.

**``output_to_user`` warning**: The dual-LLM JSON envelope is shared with ``tool_background`` finish,
where ``output_to_user`` may be false (silent recap). On **foreground** chat completions it must be
true. If the model returns false anyway (schema allows any boolean; prompts say true here), we log
``run_turn ... output_to_user=false (expected true for chat branch)`` so traces can flag
prompt/model confusion, not a parser bug.

**User-visible reply timing (tools on)**: For ``TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL`` and a
normal user round, the foreground chat completion (no ``tools`` param) finishes first; the string
returned on ``CompanionTurnResult`` / persisted as the main chat-track assistant turn comes from that
foreground parse. ``start_tool_background_job`` then runs the tool-model loop in a background thread;
``run_turn`` does **not** await that loop. Maintenance inner ticks skip the foreground envelope; see
``companion/AGENTS.md`` (Async tool_background) for the product-facing summary.

**Bootstrap (``USER_CHAT_BOOTSTRAP``)**: In-turn rounds that include ``tool_calls`` push non-empty
assistant ``content`` immediately via ``bootstrap_interim_output_sink`` (WebSocket
``outbound_queue``). Terminal rounds (no ``tool_calls``) use only the usual end-of-turn WS frame.

TODO(tool-bg-idle-starves-user-chat): Hung maintenance ``tool_background`` leaves
``CompanionSession.tool_bg_idle`` cleared; the next proactive or user ``run_turn`` blocks here
while the WebSocket ``turn_lock`` holder waits, so burst USER_MESSAGE can show only
``user-input`` with no ``chat`` (see ``chat.py`` USER_MESSAGE path, ``tool_background.py``).
Issues: https://github.com/NascentCore/inty/issues/3123 (orchestration),
https://github.com/NascentCore/inty/issues/3113 (WS turn_lock).
"""

from __future__ import annotations

import asyncio
import contextvars
import os
import threading
import time
import uuid
from datetime import datetime
from contextlib import nullcontext
from copy import deepcopy
from typing import Any

from loguru import logger

from app.core.config import global_config_loaded_from_config_yaml
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.utils.config import CompanionMemoryBootstrapType
from app.core.companion_harness.llm.langsmith_invocation_extra import (
    SOURCE_BOOTSTRAP_TRACK,
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
from app.core.companion_harness.memory.memory_store import MemoryStore
from .proactive_chat import (
    PROACTIVE_CHAT_SYNTHETIC_SYSTEM_MESSAGE,
    PROACTIVE_CHAT_TRANSCRIPT_USER_MARKER,
    build_proactive_chat_transcript_user_marker,
)
from app.core.companion_harness.companion.bootstrap import (
    interactive_bootstrap_active,
)
from app.core.companion_harness.prompting.bundle import PromptBundle
from .message_format import openai_assistant_message_dict
from .models import (
    CompanionTurnTrack,
    CompanionTurnResult,
    ContextMeta,
    InnerTickActivity,
    load_context_meta,
    transcript_relative_path_for_turn_persistence,
)
from .prompt_stack import (
    append_runtime_output_format_system_message,
    refresh_companion_turn_prompt_stack,
)
from .runtime_channel import TurnRuntimeContext
from .turn_deps import CompanionTurnDeps
from .turn_track import turn_flags_for_track
from .prompts.system_messages import (
    build_system_messages_for_chat_track,
    build_system_messages_for_inner_tick_autonomy,
    build_system_messages_for_inner_tick_maintenance,
    build_system_messages_for_tool_track,
)
from .dual_llm_chat_branch_envelope import (
    DUAL_LLM_CHAT_RESPONSE_FORMAT,
    split_dual_llm_chat_branch_message,
)
from .turn_pipeline import (
    build_companion_turn_prompt_plan,
    load_companion_turn_state,
    resolve_turn_runtime_flags,
)
from app.core.companion_harness.tools.companion_tool_definitions import (
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST,
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_AUTONOMY,
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
)
from app.core.companion_harness.tools.companion_tool_runtime import (
    execute_tool_call as repl_execute_tool_call,
)
from app.core.companion_harness.tools.runtime import (
    resolve_official_assistant_tool_loop_async,
)
from app.core.companion_harness.tools.tool_background import (
    ToolOutputEvent,
    _insert_system_message,
    push_output_event,
    start_tool_background_job,
)
from .turn_routes import (
    BootstrapInterimOutput,
    BootstrapInterimOutputSink,
    TurnRouteMode,
)
from .utc import (
    strip_leading_transcript_timestamp_prefixes,
    utc_iso_ts,
    utc_now,
)
from .implicit_signal_messages import (
    USER_SIGNED_ON_TRIGGER_USER_TEXT,
    implicit_user_signed_on_chat_turn,
)
from .inner_tick_schedule import transcript_tail_message_uuid
from .llm_chat_runtime import (
    companion_turn_langsmith_parent_trace_id_str,
    create_companion_turn_root_run,
    end_companion_turn_root_run_safe,
    langsmith_llm_run_id_from_completion,
    langsmith_trace_id_from_completion,
)
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)

CHAT_TRACK_RESPONSE_MESSAGE_TITLE = "## Response from the chat track"
_BOOTSTRAP_SYNC_MAX_TOOL_ROUNDS = 24


class CompanionToolBackgroundStartedError(RuntimeError):
    """Raised when foreground turn fails after ``tool_background`` ownership moved out."""

    companion_tool_background_started = True

    def __init__(self, original_exception: Exception) -> None:
        self.original_exception = original_exception
        super().__init__(str(original_exception))


def _replace_leading_system_messages_multi(
    messages: list[dict[str, Any]],
    system_messages: list[dict[str, Any]],
    *,
    stack_depth: int,
) -> list[dict[str, Any]]:
    """Replace the first ``stack_depth`` system messages (MemoryStore stack) with ``system_messages``.

    In dual-LLM invocation turn, 把消息列表开头那几段「人设/记忆」系统提示换成 chat 或 tool 各自需要的版本，同时完整保留后面的聊天记录、时间上下文和当前用户输入。
    """
    return [*system_messages, *messages[stack_depth:]]


def _async_dual_llm_system_message_variants(
    *,
    store: MemoryStore,
    bundle: PromptBundle,
    context: ContextMeta,
    memory_bootstrap_type: str,
    inner_tick_turn: bool,
    route_inner_activity: InnerTickActivity,
    runtime_context: TurnRuntimeContext,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Foreground ``chat_track`` vs tool-path stacks for ``ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL``.

    Implicit sign-on rounds never reach this helper (they use ``CHAT_ONLY_SYNC``).
    """
    tick_proactive = (
        inner_tick_turn
        and route_inner_activity == InnerTickActivity.PROACTIVE_CHAT
    )
    if inner_tick_turn and not tick_proactive:
        match route_inner_activity:
            case InnerTickActivity.MAINTENANCE:
                tool_system_msgs = (
                    build_system_messages_for_inner_tick_maintenance(
                        bundle, context, store
                    )
                )
            case InnerTickActivity.AUTONOMY:
                tool_system_msgs = (
                    build_system_messages_for_inner_tick_autonomy(
                        bundle, context, store
                    )
                )
            case _:
                raise RuntimeError(
                    "unexpected inner-tick activity for async tool path: "
                    f"{route_inner_activity.value}"
                )
    else:
        tool_system_msgs = build_system_messages_for_tool_track(bundle, context)
    chat_system_msgs = build_system_messages_for_chat_track(
        bundle,
        context,
        memory_bootstrap_type,
    )
    tool_system_msgs = append_runtime_output_format_system_message(
        system_messages=tool_system_msgs,
        bundle=bundle,
        runtime_context=runtime_context,
    )
    chat_system_msgs = append_runtime_output_format_system_message(
        system_messages=chat_system_msgs,
        bundle=bundle,
        runtime_context=runtime_context,
    )
    return tool_system_msgs, chat_system_msgs


async def _run_bootstrap_track_sync_tool_loop(
    *,
    store: MemoryStore,
    llm_client: CompanionLLMClient,
    messages: list[dict[str, Any]],
    tools_for_turn: list[dict[str, Any]],
    memory_bootstrap_type: str,
    repository_only_store_text: bool,
    trace_id: str,
    user_text: str,
    ts_user: datetime,
    user_msg_uuid: str,
    transcript_rel: str,
    bootstrap_interim_output_sink: BootstrapInterimOutputSink | None,
) -> tuple[str, str, str, bool, str | None]:
    """In-turn chat + tools for ``USER_CHAT_BOOTSTRAP`` (no dual-LLM / tool_background).

    Persists the user transcript row first, then non-empty assistant ``content`` from each LLM
    round (via callback) so JSONL order is always user → assistant(s). Interim rounds with
    ``tool_calls`` may also push via ``bootstrap_interim_output_sink``. Caller must not append
    the user row again at turn end.
    """
    store.append_jsonl_record(
        transcript_rel,
        {
            "role": "user",
            "content": user_text,
            "ts": ts_user.isoformat(),
            "uuid": user_msg_uuid,
            "trace_id": trace_id,
        },
    )
    working_messages = deepcopy(messages)
    loop_tools = list(tools_for_turn)
    chat_model = llm_client.resolve_model("chat")
    allow = MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP

    def _chat_sync(
        msgs: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> Any:
        return llm_client.chat_completion(
            messages=msgs,
            model=chat_model,
            tools=tools,
            scene=LLM_SCENE_CHAT,
            langsmith_extra=invocation_extra(source=SOURCE_BOOTSTRAP_TRACK),
        )

    t_api = time.perf_counter()
    initial_resp = await asyncio.to_thread(
        _chat_sync, working_messages, loop_tools
    )
    langsmith_trace_acc = langsmith_trace_id_from_completion(initial_resp) or ""
    langsmith_llm_run_acc = (
        langsmith_llm_run_id_from_completion(initial_resp) or ""
    )

    async def execute_tool_call(
        name: str, raw_arguments: str
    ) -> tuple[str, str | None]:
        result = await repl_execute_tool_call(
            store,
            name,
            raw_arguments,
            write_allowlist=allow,
            repository_only_store_text=repository_only_store_text,
        )
        return result, None

    async def continue_chat(
        messages_with_tool_results: list[dict[str, Any]],
    ) -> tuple[Any, str | None]:
        nonlocal loop_tools
        next_resp = await asyncio.to_thread(
            _chat_sync, messages_with_tool_results, loop_tools
        )
        nonlocal langsmith_trace_acc, langsmith_llm_run_acc
        tid = langsmith_trace_id_from_completion(next_resp)
        rid = langsmith_llm_run_id_from_completion(next_resp)
        if tid:
            langsmith_trace_acc = tid
        if rid:
            langsmith_llm_run_acc = rid
        return next_resp, tid

    async def _after_tool_messages_appended(
        messages_with_tool_results: list[dict[str, Any]],
    ) -> None:
        nonlocal loop_tools
        loop_tools = refresh_companion_turn_prompt_stack(
            store=store,
            memory_bootstrap_type=memory_bootstrap_type,
            inner_tick_turn=False,
            inner_tick_activity=InnerTickActivity.MAINTENANCE,
            messages=messages_with_tool_results,
            track=CompanionTurnTrack.USER_CHAT_BOOTSTRAP,
        )

    round_index = 0
    skip_final_transcript_assistant_row = False
    last_interim_assistant_msg_uuid: str | None = None

    async def _on_bootstrap_assistant_message(message: Any) -> None:
        nonlocal round_index
        nonlocal langsmith_trace_acc
        nonlocal langsmith_llm_run_acc
        nonlocal skip_final_transcript_assistant_row
        nonlocal last_interim_assistant_msg_uuid
        round_index += 1
        body = (message.content or "").strip()
        if not body:
            return
        had_tool_calls = bool(getattr(message, "tool_calls", None) or [])
        ls_trace = langsmith_trace_acc
        ls_run = langsmith_llm_run_acc
        assistant_msg_uuid = str(uuid.uuid4())
        store.append_jsonl_record(
            transcript_rel,
            {
                "role": "assistant",
                "content": body,
                "ts": utc_iso_ts(),
                "uuid": assistant_msg_uuid,
                "reply_to": user_msg_uuid,
                "source": "chat",
                "trace_id": trace_id,
            },
        )
        last_interim_assistant_msg_uuid = assistant_msg_uuid
        if not had_tool_calls:
            skip_final_transcript_assistant_row = True
        if bootstrap_interim_output_sink is not None and had_tool_calls:
            await bootstrap_interim_output_sink(
                BootstrapInterimOutput(
                    text=body,
                    user_msg_uuid=user_msg_uuid,
                    trace_id=trace_id,
                    langsmith_trace_id=ls_trace,
                    langsmith_run_id=ls_run,
                    round_index=round_index,
                    had_tool_calls=had_tool_calls,
                    assistant_msg_uuid=assistant_msg_uuid,
                )
            )

    loop_result = await resolve_official_assistant_tool_loop_async(
        response=initial_resp,
        openai_messages=working_messages,
        max_tool_call_rounds=_BOOTSTRAP_SYNC_MAX_TOOL_ROUNDS,
        execute_tool_call=execute_tool_call,
        continue_chat=continue_chat,
        build_assistant_tool_call_message=openai_assistant_message_dict,
        insert_system_message=_insert_system_message,
        initial_trace_id=langsmith_trace_acc or None,
        after_tool_messages_appended=_after_tool_messages_appended,
        on_assistant_message=_on_bootstrap_assistant_message,
    )
    if loop_result.trace_id:
        langsmith_trace_acc = loop_result.trace_id
    final_msg = loop_result.response.choices[0].message
    last_text = (final_msg.content or "").strip()
    approx_ctx_chars = sum(
        len(str(m.get("content") or "")) for m in loop_result.messages
    )
    logger.info(
        "run_turn bootstrap_track llm_done model={} chat_completions_ms={:.0f} "
        "approx_ctx_chars={} trace_id={}",
        chat_model,
        (time.perf_counter() - t_api) * 1000.0,
        approx_ctx_chars,
        trace_id,
    )
    return (
        last_text,
        langsmith_trace_acc,
        langsmith_llm_run_acc,
        skip_final_transcript_assistant_row,
        last_interim_assistant_msg_uuid,
    )


async def _await_tool_background_idle_if_configured(
    tool_bg_idle_event: threading.Event | None,
    *,
    idle_wait_timeout_sec: float,
    scope_registry_key: str,
) -> None:
    # TODO(tool-bg-idle-starves-user-chat): Timeout logs WARNING but still proceeds;
    # a stuck tool_bg thread can wedge every later turn on this session until restart.
    # https://github.com/NascentCore/inty/issues/3123
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


# TODO(companion-multimodal-user-turn): Phase 1c — ``user_turn: CompanionUserTurnInput``
# https://github.com/NascentCore/inty/issues/3293
# through turn core; transcript user row uses ``user_turn.to_transcript_text()`` (caption
# or ``"[image]"``); memory pipeline stays text-only. LLM tail content assembled in
# turn_pipeline when chat model accepts IMAGE input.
# TODO(track-driven-system-messages-building): Inline calling of this function in the callers.
async def _run_companion_turn_core(
    user_text: str,
    *,
    track: CompanionTurnTrack,
    deps: CompanionTurnDeps,
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

    返回 ``CompanionTurnResult``（``assistant_text`` 与可选 ``significance_perception``）。
    有工具且走上述异步路由时：普通用户轮的 ``assistant_text`` 仅反映**已结束的前台** envelope，**不等待**
    ``tool_background`` 内 tool 模型多轮跑完；维护性 inner tick 跳过前台时 ``assistant_text`` 可为空。
    """
    store = deps.store
    llm_client = deps.llm_client
    transcript_compaction = deps.transcript_compaction
    transcript_llm_window_max_messages = deps.transcript_llm_window_max_messages
    repository_only_store_text = deps.repository_only_store_text
    memory_bootstrap_type = deps.memory_bootstrap_type
    runtime_context = deps.runtime_context
    background_output_sink = deps.background_output_sink
    preset_user_msg_uuid = deps.preset_user_msg_uuid
    langsmith_parent_run_enabled = deps.langsmith_parent_run_enabled
    tool_bg_idle_event = deps.tool_bg_idle_event
    bootstrap_interim_output_sink = deps.bootstrap_interim_output_sink
    t0 = time.perf_counter()
    paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    inner_tick_turn, route_inner_activity = turn_flags_for_track(track)
    implicit_signal_bundle = runtime_context.implicit_signal_bundle

    runtime_flags = resolve_turn_runtime_flags(
        track=track,
        user_text=user_text,
        implicit_signal_bundle=implicit_signal_bundle,
    )
    user_text = runtime_flags.effective_user_text
    tick_proactive = runtime_flags.tick_proactive
    route_inner_activity = runtime_flags.route_inner_activity
    implicit_sign_on_turn = runtime_flags.implicit_sign_on_turn

    logger.info(
        "run_turn start scope={} track={} user_chars={} inner_tick_turn={} inner_tick_activity={}",
        store.scope.registry_key(),
        track.value,
        len(user_text),
        inner_tick_turn,
        route_inner_activity.value if inner_tick_turn else "-",
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
        idle_wait_timeout_sec = float(
            llm_client.config.async_chat_front_timeout_sec
        )
    # TODO(tool-bg-idle-starves-user-chat): Maintenance often ends with tool_background still running;
    # the next turn waits on ``tool_bg_idle`` here while holding WS ``turn_lock``.
    # https://github.com/NascentCore/inty/issues/3123
    await _await_tool_background_idle_if_configured(
        tool_bg_idle_event,
        idle_wait_timeout_sec=idle_wait_timeout_sec,
        scope_registry_key=store.scope.registry_key(),
    )

    loaded_state = load_companion_turn_state(
        store=store,
        inner_tick_turn=inner_tick_turn,
        route_inner_activity=route_inner_activity,
        transcript_llm_window_max_messages=transcript_llm_window_max_messages,
    )
    if tick_proactive:
        user_text = build_proactive_chat_transcript_user_marker(
            loaded_state.loaded_transcript
        )
    context = loaded_state.context
    bundle = loaded_state.bundle
    ts_user = utc_now()
    prompt_plan = build_companion_turn_prompt_plan(
        store=store,
        loaded_state=loaded_state,
        user_text=user_text,
        tail_user_ts=ts_user,
        memory_bootstrap_type=memory_bootstrap_type,
        track=track,
        tick_proactive=tick_proactive,
        implicit_sign_on_turn=implicit_sign_on_turn,
        runtime_context=runtime_context,
        transcript_compaction=transcript_compaction,
    )
    tools_for_turn = prompt_plan.tools_for_turn
    route_mode = prompt_plan.route_mode
    messages = prompt_plan.messages
    use_dual_structured_chat = prompt_plan.use_dual_structured_chat
    user_msg_uuid = (
        preset_user_msg_uuid if preset_user_msg_uuid else str(uuid.uuid4())
    )
    trace_id = str(uuid.uuid4())
    langsmith_trace_acc = ""
    langsmith_llm_run_acc = ""

    last_text = ""
    significance_meta: dict[str, Any] | None = None
    tool_background_started = False
    bootstrap_skip_final_transcript_assistant_row = False
    bootstrap_last_interim_assistant_msg_uuid: str | None = None
    t_loop = time.perf_counter()

    llm_runtime_bind_token: (
        contextvars.Token[LlmRuntimeEventBind | None] | None
    ) = None
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

        langsmith_parent_run = create_companion_turn_root_run(
            inty_trace_id=trace_id,
            user_msg_uuid=user_msg_uuid,
            chat_model=llm_client.resolve_model("chat"),
            tool_model=llm_client.resolve_model("tool"),
            user_id=context.user_id,
            companion_id=context.companion_id,
            parent_run_enabled=langsmith_parent_run_enabled,
            companion_turn_track=track,
            inner_tick_turn=inner_tick_turn,
            inner_tick_activity=(
                route_inner_activity if inner_tick_turn else None
            ),
            implicit_user_signed_on=implicit_sign_on_turn,
            transcript_newest_message_uuid=(
                transcript_tail_message_uuid(store) if inner_tick_turn else None
            ),
        )
        _ls_tid = companion_turn_langsmith_parent_trace_id_str(
            langsmith_parent_run
        )
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
                route_mode
                == TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL,
            )

        _langsmith_cm = nullcontext()
        if langsmith_parent_run is not None:
            from langsmith.run_helpers import tracing_context

            _langsmith_cm = tracing_context(parent=langsmith_parent_run)

        with _langsmith_cm:
            try:
                if track == CompanionTurnTrack.USER_CHAT_BOOTSTRAP:
                    rel_tr_bootstrap = (
                        transcript_relative_path_for_turn_persistence(
                            inner_tick_turn=False,
                            inner_tick_activity=route_inner_activity,
                        )
                    )
                    (
                        last_text,
                        langsmith_trace_acc,
                        langsmith_llm_run_acc,
                        bootstrap_skip_final_transcript_assistant_row,
                        bootstrap_last_interim_assistant_msg_uuid,
                    ) = await _run_bootstrap_track_sync_tool_loop(
                        store=store,
                        llm_client=llm_client,
                        messages=messages,
                        tools_for_turn=tools_for_turn,
                        memory_bootstrap_type=memory_bootstrap_type,
                        repository_only_store_text=repository_only_store_text,
                        trace_id=trace_id,
                        user_text=user_text,
                        ts_user=ts_user,
                        user_msg_uuid=user_msg_uuid,
                        transcript_rel=rel_tr_bootstrap,
                        bootstrap_interim_output_sink=(
                            bootstrap_interim_output_sink
                        ),
                    )
                    logger.info(
                        "run_turn loop_done bootstrap_track loop_total_ms={:.0f}",
                        (time.perf_counter() - t_loop) * 1000.0,
                    )
                elif (
                    route_mode
                    == TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL
                ):
                    tool_system_msgs, chat_system_msgs = (
                        _async_dual_llm_system_message_variants(
                            store=store,
                            bundle=bundle,
                            context=context,
                            memory_bootstrap_type=memory_bootstrap_type,
                            inner_tick_turn=inner_tick_turn,
                            route_inner_activity=route_inner_activity,
                            runtime_context=runtime_context,
                        )
                    )
                    _stack_depth = len(prompt_plan.system_messages)
                    chat_msgs = _replace_leading_system_messages_multi(
                        messages,
                        chat_system_msgs,
                        stack_depth=_stack_depth,
                    )
                    tool_msgs = _replace_leading_system_messages_multi(
                        messages,
                        tool_system_msgs,
                        stack_depth=_stack_depth,
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

                    skip_foreground_envelope = (
                        inner_tick_turn and not tick_proactive
                    )
                    if skip_foreground_envelope:
                        logger.info(
                            "run_turn inner_tick skip foreground envelope "
                            "inner_tick_activity={} model_chat={}",
                            route_inner_activity.value,
                            chat_model,
                        )
                        last_text = ""
                        significance_meta = None
                        tool_msgs_for_bg = deepcopy(tool_msgs)
                        force_tools_first_round = True
                    else:
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
                                    high_reasoning=tick_proactive,
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
                                model=chat_model.id_on_provider,
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
                        tool_model=tool_model,
                        user_msg_uuid=user_msg_uuid,
                        trace_id=trace_id,
                        tools=tools_for_turn,
                        on_event=_kernel_bg_on_event,
                        execute_tool_call_fn=repl_execute_tool_call,
                        client=llm_client.sync_client_for_route("tool"),
                        chat_completions_sync=llm_client.chat_completions_sync,
                        write_allowlist=(
                            MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_AUTONOMY
                            if track == CompanionTurnTrack.INNER_TICK_AUTONOMY
                            else MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST
                        ),
                        repository_only_store_text=repository_only_store_text,
                        main_event_loop=asyncio.get_running_loop(),
                        langsmith_parent_run=langsmith_parent_run,
                        memory_bootstrap_type=memory_bootstrap_type,
                        inner_tick_turn=inner_tick_turn,
                        inner_tick_activity=route_inner_activity,
                        runtime_context=runtime_context,
                        companion_turn_track=track,
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
                    llm_scene = (
                        LLM_SCENE_INNER_TICK
                        if inner_tick_turn and not tick_proactive
                        else LLM_SCENE_CHAT
                    )
                    response_format = (
                        DUAL_LLM_CHAT_RESPONSE_FORMAT
                        if use_dual_structured_chat
                        else None
                    )
                    if implicit_sign_on_turn:
                        greet_feats = (
                            global_config_loaded_from_config_yaml.app.features
                        )
                        greet_timeout_sec = float(
                            greet_feats.companion_implicit_sign_on_greeting_llm_timeout_sec
                        )
                        greet_max_attempts = int(
                            greet_feats.companion_implicit_sign_on_greeting_llm_max_attempts
                        )
                        resp = await llm_client.chat_completion_with_retrial(
                            messages=messages,
                            model=resolved_model,
                            tools=None,
                            tool_choice=None,
                            response_format=response_format,
                            scene=llm_scene,
                            langsmith_extra=None,
                            high_reasoning=tick_proactive,
                            max_attempts=greet_max_attempts,
                            per_attempt_timeout_sec=greet_timeout_sec,
                            trace_id=trace_id,
                            attempt_log_label="implicit_sign_on_greeting",
                        )
                    else:
                        resp = llm_client.chat_completion(
                            messages=messages,
                            model=resolved_model,
                            tools=None,
                            response_format=response_format,
                            scene=llm_scene,
                            high_reasoning=tick_proactive,
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
                    logger.info(
                        "run_turn loop_done single_shot route={} loop_total_ms={:.0f}",
                        route_mode.value,
                        (time.perf_counter() - t_loop) * 1000.0,
                    )
            except BaseException as exc:
                wrap_tool_background_exception = (
                    tool_background_started and isinstance(exc, Exception)
                )
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
                if wrap_tool_background_exception:
                    raise CompanionToolBackgroundStartedError(exc) from exc
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

    # 持久化 transcript
    # TODO(code-path-straightforwardness): refactor this function to accept
    # the transcript path (resolved at the time when turn track is determined) as an argument.
    rel_tr = (
        paths.transcript
        if implicit_sign_on_turn
        else transcript_relative_path_for_turn_persistence(
            inner_tick_turn=inner_tick_turn,
            inner_tick_activity=route_inner_activity,
        )
    )
    assistant_msg_uuid = (
        bootstrap_last_interim_assistant_msg_uuid
        if bootstrap_last_interim_assistant_msg_uuid is not None
        else str(uuid.uuid4())
    )
    if implicit_sign_on_turn:
        sign_on_row: dict[str, Any] = {
            "role": "user",
            "content": USER_SIGNED_ON_TRIGGER_USER_TEXT,
            "ts": ts_user.isoformat(),
            "uuid": user_msg_uuid,
            "trace_id": trace_id,
            "implicit_user_signed_on": True,
        }
        store.append_jsonl_record(rel_tr, sign_on_row)
    else:
        user_row: dict[str, Any] = {
            "role": "user",
            "content": user_text,
            "ts": ts_user.isoformat(),
            "uuid": user_msg_uuid,
        }
        if inner_tick_turn:
            user_row["inner_tick"] = True
        if tick_proactive:
            # TODO: use enum for message type, not bool proactive_chat
            user_row["proactive_chat"] = True
        if track == CompanionTurnTrack.INNER_TICK_SCHEDULED:
            user_row["scheduled"] = True
        user_row["trace_id"] = trace_id
        if track != CompanionTurnTrack.USER_CHAT_BOOTSTRAP:
            store.append_jsonl_record(rel_tr, user_row)
    last_text = strip_leading_transcript_timestamp_prefixes(last_text)
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
    if not bootstrap_skip_final_transcript_assistant_row:
        store.append_jsonl_record(rel_tr, assistant_row)

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
    transcript_user_content = (
        USER_SIGNED_ON_TRIGGER_USER_TEXT if implicit_sign_on_turn else user_text
    )
    return CompanionTurnResult(
        assistant_text=last_text,
        significance_perception=significance_meta,
        user_msg_uuid=user_msg_uuid,
        assistant_msg_uuid=assistant_msg_uuid,
        trace_id=trace_id,
        langsmith_trace_id=langsmith_trace_acc,
        langsmith_run_id=langsmith_llm_run_acc,
        tool_background_started=tool_background_started,
        assistant_source=runtime_flags.turn_type,
        inner_tick_activity=(
            route_inner_activity.value if inner_tick_turn else None
        ),
        turn_start_context_mode=context.context_mode,
        transcript_compaction=prompt_plan.transcript_compaction,
        transcript_user_content=transcript_user_content,
    )


async def run_companion_user_chat_turn(
    user_text: str,
    *,
    deps: CompanionTurnDeps,
) -> CompanionTurnResult:
    implicit_signal_bundle = deps.runtime_context.implicit_signal_bundle
    if (
        implicit_signal_bundle is not None
        and implicit_user_signed_on_chat_turn(
            implicit_signal_bundle=implicit_signal_bundle,
            inner_tick_turn=False,
        )
    ):
        raise ValueError(
            "implicit sign-on greeting must use run_companion_implicit_sign_on_greeting_turn"
        )
    context = load_context_meta(store=deps.store)
    track = (
        CompanionTurnTrack.USER_CHAT_BOOTSTRAP
        if interactive_bootstrap_active(
            feature_enabled=(
                deps.memory_bootstrap_type
                == CompanionMemoryBootstrapType.USER_INTERACTIVE.value
            ),
            meta=context,
        )
        else CompanionTurnTrack.USER_CHAT
    )
    return await _run_companion_turn_core(user_text, track=track, deps=deps)


async def run_companion_implicit_sign_on_greeting_turn(
    user_text: str,
    *,
    deps: CompanionTurnDeps,
) -> CompanionTurnResult:
    implicit_signal_bundle = deps.runtime_context.implicit_signal_bundle
    assert implicit_signal_bundle is not None
    assert implicit_user_signed_on_chat_turn(
        implicit_signal_bundle=implicit_signal_bundle,
        inner_tick_turn=False,
    )
    return await _run_companion_turn_core(
        user_text,
        track=CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING,
        deps=deps,
    )


async def run_companion_inner_tick_proactive_chat_turn(
    *,
    deps: CompanionTurnDeps,
) -> CompanionTurnResult:
    return await _run_companion_turn_core(
        "",
        track=CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT,
        deps=deps,
    )


async def run_companion_inner_tick_scheduled_turn(
    scheduled_user_text: str,
    *,
    deps: CompanionTurnDeps,
) -> CompanionTurnResult:
    assert (
        scheduled_user_text.strip()
    ), "run_companion_inner_tick_scheduled_turn requires non-empty scheduled_user_text"
    return await _run_companion_turn_core(
        scheduled_user_text,
        track=CompanionTurnTrack.INNER_TICK_SCHEDULED,
        deps=deps,
    )


async def run_companion_inner_tick_maintenance_turn(
    *,
    deps: CompanionTurnDeps,
) -> CompanionTurnResult:
    return await _run_companion_turn_core(
        "",
        track=CompanionTurnTrack.INNER_TICK_MAINTENANCE,
        deps=deps,
    )


async def run_inner_tick_autonomy(
    *,
    deps: CompanionTurnDeps,
) -> CompanionTurnResult:
    """AUTONOMY inner tick: open tool set, **never** delivers to the user.

    Same async foreground/tool-background lifecycle as maintenance, but with
    an open tool set and the autonomy system prompt slice that instructs the
    model to read ``LIFE_CURRENTS.md``, do real work (web, image, MemoryStore
    writes), and write progress back — all silently.
    """
    return await _run_companion_turn_core(
        "",
        track=CompanionTurnTrack.INNER_TICK_AUTONOMY,
        deps=deps,
    )
