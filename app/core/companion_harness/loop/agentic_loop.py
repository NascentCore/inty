"""Production agentic loop for queue-served user turns.

Runs one user-facing turn through either a single language model with in-turn
tool calling or a dual-model chat-plus-tool path. User-visible assistant text is
written to the durable outbound queue as it is produced so channels can deliver
partial replies before the turn finishes.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from app.core.config import global_config_loaded_from_config_yaml

from app.core.companion_harness.agentic_companion.output_queue import (
    OutputQueue,
    OutputQueueAppendInput,
)
from app.core.companion_harness.agentic_companion.types import OutputMessageKind
from app.core.companion_harness.agentic_companion.types import (
    AGENT_INITIATED_USER_MESSAGE_BATCH_PREFIX,
    UserMessageBatch,
)
from app.core.companion_harness.agentic_companion.types import (
    GeneratedImageRef,
)
from app.core.companion_harness.companion.dual_llm_foreground_chat import (
    DualLlmForegroundChatInput,
    run_dual_llm_foreground_chat,
)
from app.core.companion_harness.companion.in_turn_sync_tool_loop import (
    InTurnSyncToolLoopResult,
)
from app.core.companion_harness.companion.turn_tail_user import (
    append_turn_track_tail_user_transcript_rows,
)
from app.core.companion_harness.companion.llm_chat_runtime import (
    langsmith_llm_run_id_from_completion,
    langsmith_trace_id_from_completion,
)
from app.core.llms.client import (
    AsyncLlmClient,
    LlmClient,
)
from app.core.companion_harness.companion.message_format import (
    openai_assistant_message_dict,
)
from app.core.companion_harness.companion.dual_llm_chat_branch_envelope import (
    DUAL_LLM_CHAT_RESPONSE_FORMAT,
    split_dual_llm_chat_branch_message,
)
from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    user_visible_assistant_text,
)
from app.core.companion_harness.companion.proactive_chat_envelope import (
    PROACTIVE_CHAT_RESPONSE_FORMAT,
    split_proactive_chat_message,
)
from app.core.companion_harness.companion.turn_routes import (
    BootstrapInterimOutput,
)
from app.core.companion_harness.companion.utc import utc_iso_ts
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.prompt_builder import (
    prompt_messages_to_openai_dicts,
)
from app.core.companion_harness.tools.companion_tool_runtime import (
    execute_tool_call,
    execute_tool_call as repl_execute_tool_call,
)
from app.core.companion_harness.tools.runtime import (
    insert_openai_system_message,
    resolve_openai_tool_call_loop_async,
)
from app.core.companion_harness.tools.tool_background import (
    ToolOutputEvent,
    run_tool_background_loop,
)
from app.core.companion_harness.tools.image_gate import (
    generated_image_meta_from_asset_record,
    list_image_asset_records,
)

from .context import AgenticLoopContext, AgenticLoopOutput
from .runtime_system_clauses import apply_agentic_loop_runtime_system_clauses

_DRAIN_SENTINEL: ToolOutputEvent | None = None


def _generated_image_refs_since(
    store: MemoryStore,
    baseline_index: int,
) -> tuple[GeneratedImageRef, ...]:
    records = list_image_asset_records(store)
    if baseline_index < 0 or baseline_index > len(records):
        return ()
    refs: list[GeneratedImageRef] = []
    for row in records[baseline_index:]:
        meta = generated_image_meta_from_asset_record(row)
        if meta is not None:
            refs.append(GeneratedImageRef.model_validate(meta))
    return tuple(refs)


def _append_user_transcript_row(
    *,
    store: MemoryStore,
    context: AgenticLoopContext,
) -> None:
    """Persist the claimed user turn before AgenticLoop emits assistant rows.

    Pairs with ``in_turn_sync_persisted_transcript`` in ``turn.py``: turn end must
    not append the user row again when AgenticLoop owns persistence.

    Implicit sign-on greeting keeps the dedicated ``implicit_user_signed_on`` row
    in ``turn.py``; skip generic tail persistence here.
    """
    if (
        context.companion_turn_track
        == CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING
    ):
        return
    append_turn_track_tail_user_transcript_rows(
        store,
        context.transcript_rel,
        tail_user_messages=context.tail_user_messages,
        trace_id=context.trace_id,
        track=context.companion_turn_track,
    )


@dataclass
class _UserVisibleOutputAppender:
    """Collects user-visible assistant lines into the outbound queue for one turn.

    Filters silent or internal-only text, persists each visible line with batch
    correlation, and records outbound ids for the turn result.
    """

    output_queue: OutputQueue
    batch: UserMessageBatch
    store: MemoryStore
    image_asset_baseline: int
    persisted_ids: list[str] = field(default_factory=list)

    def _output_correlation_message_ids(self) -> tuple[str, ...]:
        """Agent-initiated batches correlate in LangSmith only; OutputQueue rows use ``()``."""
        if self.batch.batch_id.startswith(
            AGENT_INITIATED_USER_MESSAGE_BATCH_PREFIX
        ):
            return ()
        return self.batch.message_ids

    async def append_visible_message(
        self,
        *,
        kind: OutputMessageKind,
        text: str,
        trace_id: str,
        langsmith_trace_id: str,
        langsmith_run_id: str,
        turn_recall: str | None = None,
        tool_background_started: bool = False,
    ) -> None:
        visible = user_visible_assistant_text(text)
        if visible is None:
            return
        ready = await self.output_queue.append_visible_message(
            OutputQueueAppendInput(
                kind=kind,
                batch_id=self.batch.batch_id,
                text=visible,
                message_ids=self._output_correlation_message_ids(),
                trace_id=trace_id,
                langsmith_trace_id=langsmith_trace_id,
                langsmith_run_id=langsmith_run_id,
                turn_recall=turn_recall,
                tool_background_started=tool_background_started,
                generated_images=(
                    _generated_image_refs_since(
                        self.store,
                        self.image_asset_baseline,
                    )
                    if kind == OutputMessageKind.USER_REPLY
                    else ()
                ),
            )
        )
        self.persisted_ids.append(ready.message_id)


class _DomainToolBackgroundAppendSink:
    """Bridges background tool-loop events into the outbound queue.

    Tool work may emit user-visible follow-ups from a worker thread; this sink
    accepts those events synchronously and drains them asynchronously into the
    same outbound appender used for foreground lines.
    """

    def __init__(
        self, *, appender: _UserVisibleOutputAppender, trace_id: str
    ) -> None:
        self._appender = appender
        self._trace_id = trace_id
        self._pending: asyncio.Queue[ToolOutputEvent | None] = asyncio.Queue()
        self._drainer: asyncio.Task[None] | None = None

    def __call__(self, event: ToolOutputEvent) -> None:
        if not event.output_to_user:
            return
        if user_visible_assistant_text(event.text) is None:
            return
        self._ensure_drainer()
        self._pending.put_nowait(event)

    def _ensure_drainer(self) -> None:
        if self._drainer is None:
            self._drainer = asyncio.create_task(self._drain())

    async def _drain(self) -> None:
        while True:
            event = await self._pending.get()
            if event is None:
                return
            await self._appender.append_visible_message(
                kind=OutputMessageKind.TOOL_BACKGROUND,
                text=event.text,
                trace_id=event.trace_id or self._trace_id,
                langsmith_trace_id=event.langsmith_trace_id,
                langsmith_run_id=event.langsmith_run_id,
                turn_recall=event.turn_recall,
            )

    async def flush(self) -> None:
        if self._drainer is None:
            return
        self._pending.put_nowait(_DRAIN_SENTINEL)
        await self._drainer
        self._drainer = None


async def _run_prompt_plan_tool_loop(
    context: AgenticLoopContext,
    *,
    store: MemoryStore,
    llm_client: AsyncLlmClient,
    interim_output_sink,
    max_tool_call_rounds: int,
) -> InTurnSyncToolLoopResult:
    """Single-LLM tool loop using ``PromptPlan`` wire messages owned by this loop.

    TODO(!3629): Stop converting PromptPlan to wire dicts here; pass plan into AsyncLlmClient.
    TODO(!3630): Build langsmith_extra from LlmInvocationContext, not call-site dicts.
    """
    assert context.prompt_plan is not None
    execution = context.execution
    transcript_rel = context.transcript_rel
    trace_id = context.trace_id
    user_msg_uuid = context.user_msg_uuid
    prompt_plan = context.prompt_plan
    loop_tools = list(prompt_plan.tools)
    chat_model = llm_client.resolve_model("chat")
    allow = execution.write_allowlist
    langsmith_slice = context.langsmith.turn_slice
    langsmith_extra = langsmith_slice.foreground_invocation_extra(
        source=execution.foreground_source.value,
        extra_metadata=None,
    )

    request_messages = prompt_messages_to_openai_dicts(prompt_plan.messages)
    apply_agentic_loop_runtime_system_clauses(
        openai_messages=request_messages,
        user_text=context.user_text,
    )
    t_api = time.perf_counter()
    initial_resp = await llm_client.chat_completion(
        messages=request_messages,
        tools=loop_tools,
        tool_choice=prompt_plan.tool_choice,
        model=chat_model,
        langsmith_extra=langsmith_extra,
        high_reasoning=execution.high_reasoning,
    )
    working_messages = deepcopy(request_messages)
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
            repository_only_store_text=context.repository_only_store_text,
        )
        return result, None

    async def continue_chat(
        messages_with_tool_results: list[dict[str, Any]],
    ) -> tuple[Any, str | None]:
        next_resp = await llm_client.chat_completion(
            messages=messages_with_tool_results,
            tools=loop_tools,
            tool_choice=prompt_plan.tool_choice,
            model=chat_model,
            langsmith_extra=langsmith_extra,
            high_reasoning=execution.high_reasoning,
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
        if context.after_tool_messages_appended is not None:
            refreshed = await context.after_tool_messages_appended(
                messages_with_tool_results
            )
            if refreshed is not None:
                loop_tools = refreshed

    round_index = 0
    skip_final_transcript_assistant_row = False
    last_interim_assistant_msg_uuid: str | None = None
    emit_every_round = True

    async def _on_assistant_message(message: Any) -> None:
        nonlocal round_index
        nonlocal langsmith_trace_acc
        nonlocal langsmith_llm_run_acc
        nonlocal skip_final_transcript_assistant_row
        nonlocal last_interim_assistant_msg_uuid
        round_index += 1
        body = (message.content or "").strip()
        # TODO(!3457): Deliver interim chat while tools run — when body is empty but
        # tool_calls present, resolve visible text so user is not silent during tool
        # execution (!3456).
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
        if interim_output_sink is not None and (
            emit_every_round or had_tool_calls
        ):
            await interim_output_sink(
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

    loop_result = await resolve_openai_tool_call_loop_async(
        response=initial_resp,
        openai_messages=working_messages,
        max_tool_call_rounds=max_tool_call_rounds,
        execute_tool_call=execute_tool_call,
        continue_chat=continue_chat,
        build_assistant_tool_call_message=openai_assistant_message_dict,
        insert_system_message=insert_openai_system_message,
        initial_trace_id=langsmith_trace_acc or None,
        after_tool_messages_appended=_after_tool_messages_appended,
        on_assistant_message=_on_assistant_message,
    )
    if loop_result.trace_id:
        langsmith_trace_acc = loop_result.trace_id
    final_msg = loop_result.response.choices[0].message
    last_text = (final_msg.content or "").strip()
    approx_ctx_chars = sum(
        len(str(m.get("content") or "")) for m in loop_result.messages
    )
    logger.info(
        "prompt_plan_tool_loop llm_done model={} chat_completions_ms={:.0f} "
        "approx_ctx_chars={} trace_id={}",
        chat_model,
        (time.perf_counter() - t_api) * 1000.0,
        approx_ctx_chars,
        trace_id,
    )
    return InTurnSyncToolLoopResult(
        assistant_text=last_text,
        langsmith_trace_id=langsmith_trace_acc,
        langsmith_run_id=langsmith_llm_run_acc,
        skip_final_transcript_assistant_row=skip_final_transcript_assistant_row,
        last_interim_assistant_msg_uuid=last_interim_assistant_msg_uuid,
        loop_persisted_user_transcript=True,
    )


async def _run_chat_only_prompt_plan(
    context: AgenticLoopContext,
    *,
    llm_client: AsyncLlmClient,
    appender: _UserVisibleOutputAppender,
) -> InTurnSyncToolLoopResult:
    """Single chat completion (no tools) for greeting and inner-tick chat-only tracks.

    Mirrors the legacy single-shot contract per track: greeting completes under the
    dual-LLM structured envelope (significance + turn_recall), proactive and
    scheduled complete under the proactive envelope (``output_to_user`` may silence
    the turn), matching each track's structured-output prompt contract.
    """
    assert context.prompt_plan is not None
    track = context.companion_turn_track
    execution = context.execution
    request_messages = prompt_messages_to_openai_dicts(
        context.prompt_plan.messages
    )
    apply_agentic_loop_runtime_system_clauses(
        openai_messages=request_messages,
        user_text=context.user_text,
    )
    chat_model = llm_client.resolve_model("chat")
    langsmith_extra = context.langsmith.turn_slice.foreground_invocation_extra(
        source=execution.foreground_source.value,
        extra_metadata=None,
    )
    llm_scene = execution.llm_scene.value
    match track:
        case CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT:
            downlink_kind = OutputMessageKind.PROACTIVE
            response_format = PROACTIVE_CHAT_RESPONSE_FORMAT
        case CompanionTurnTrack.INNER_TICK_SCHEDULED:
            downlink_kind = OutputMessageKind.SCHEDULED
            response_format = PROACTIVE_CHAT_RESPONSE_FORMAT
        case CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING:
            downlink_kind = OutputMessageKind.USER_REPLY
            response_format = DUAL_LLM_CHAT_RESPONSE_FORMAT
        case _:
            downlink_kind = OutputMessageKind.USER_REPLY
            response_format = None

    t_api = time.perf_counter()
    match track:
        case CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING:
            greet_cfg = (
                global_config_loaded_from_config_yaml.agent.companion_harness.implicit_sign_on_greeting
            )
            resp = await llm_client.chat_completion_with_retrial(
                messages=request_messages,
                model=chat_model,
                tools=None,
                tool_choice=None,
                response_format=response_format,
                scene=llm_scene,
                langsmith_extra=langsmith_extra,
                high_reasoning=execution.high_reasoning,
                max_attempts=int(greet_cfg.llm_max_attempts),
                per_attempt_timeout_sec=float(greet_cfg.llm_timeout_sec),
                trace_id=context.trace_id,
                attempt_log_label="implicit_sign_on_greeting",
            )
        case _:
            resp = await llm_client.chat_completion(
                messages=request_messages,
                model=chat_model,
                tools=None,
                response_format=response_format,
                langsmith_extra=langsmith_extra,
                high_reasoning=execution.high_reasoning,
                scene=llm_scene,
            )
    langsmith_trace_acc = langsmith_trace_id_from_completion(resp) or ""
    langsmith_llm_run_acc = langsmith_llm_run_id_from_completion(resp) or ""
    msg = resp.choices[0].message
    skip_final_transcript_assistant_row = False
    significance_meta: dict[str, Any] | None = None
    turn_recall: str | None = None
    match track:
        case (
            CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT
            | CompanionTurnTrack.INNER_TICK_SCHEDULED
        ):
            proactive_split = split_proactive_chat_message(msg)
            if proactive_split.output_to_user:
                last_text = proactive_split.visible_text
            else:
                last_text = ""
                skip_final_transcript_assistant_row = True
        case CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING:
            dual_split = split_dual_llm_chat_branch_message(msg)
            last_text = dual_split.visible_text
            significance_meta = dual_split.significance_meta
            turn_recall = dual_split.turn_recall
            # Envelope contract: chat branch must set output_to_user true; false is
            # for tool_background finish envelopes only. Non-fatal model drift.
            if dual_split.output_to_user is False:
                logger.warning(
                    "chat_only_prompt_plan dual_llm envelope output_to_user=false "
                    "trace_id={} (expected true for greeting)",
                    context.trace_id,
                )
        case _:
            last_text = (msg.content or "").strip()
    approx_ctx_chars = sum(
        len(str(m.get("content") or "")) for m in request_messages
    )
    logger.info(
        "chat_only_prompt_plan llm_done model={} chat_completions_ms={:.0f} "
        "approx_ctx_chars={} trace_id={} track={}",
        chat_model,
        (time.perf_counter() - t_api) * 1000.0,
        approx_ctx_chars,
        context.trace_id,
        track.value,
    )
    if last_text and track != CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING:
        await appender.append_visible_message(
            kind=downlink_kind,
            text=last_text,
            trace_id=context.trace_id,
            langsmith_trace_id=langsmith_trace_acc,
            langsmith_run_id=langsmith_llm_run_acc,
            turn_recall=turn_recall,
        )
    return InTurnSyncToolLoopResult(
        assistant_text=last_text,
        langsmith_trace_id=langsmith_trace_acc,
        langsmith_run_id=langsmith_llm_run_acc,
        skip_final_transcript_assistant_row=skip_final_transcript_assistant_row,
        last_interim_assistant_msg_uuid=None,
        loop_persisted_user_transcript=False,
        significance_meta=significance_meta,
        turn_recall=turn_recall,
    )


class AgenticLoop:
    """Executes one queue-served user turn for bootstrap or settled chat.

    Single-model path runs in-turn tool rounds and streams each non-empty
    assistant line to the outbound queue immediately. Dual-model path runs
    foreground chat then optional background tool work with the same outbound
    streaming policy. Intended for turns that already have outbound queue and
    inbound batch correlation attached by the turn executor.

    TODO(!3456): User chat must not go silent while tools execute; deliver interim
    chat when the model omits content on tool rounds.

    TODO(!3470): Bootstrap outbound lines during tools should read like natural
    chat while working, not serial status broadcasts.

    TODO(!3459): Migrate proactive, monolog, scheduled, and dreaming turns
    to this loop instead of legacy in-turn sync paths.

    TODO(!3402): Replace bootstrap-named interim callback types with a neutral
    per-round visible-text sink shared by queue and non-queue paths.
    """

    def __init__(
        self,
        *,
        store: MemoryStore,
        llm_client: AsyncLlmClient,
        legacy_llm_client: LlmClient,
    ) -> None:
        """Bind stable agent dependencies used across loop runs."""
        self.store = store
        self.llm_client = llm_client
        self.legacy_llm_client = legacy_llm_client

    async def run_single_llm_turn(
        self, *, context: AgenticLoopContext
    ) -> AgenticLoopOutput:
        """Execute one single-LLM turn; each non-empty assistant ``content`` → ``OutputQueue``."""
        _append_user_transcript_row(store=self.store, context=context)
        appender = _UserVisibleOutputAppender(
            output_queue=context.output_queue,
            batch=context.user_message_batch,
            store=self.store,
            image_asset_baseline=len(list_image_asset_records(self.store)),
        )

        async def _emit_user_reply(interim: BootstrapInterimOutput) -> None:
            await appender.append_visible_message(
                kind=OutputMessageKind.USER_REPLY,
                text=interim.text,
                trace_id=interim.trace_id,
                langsmith_trace_id=interim.langsmith_trace_id,
                langsmith_run_id=interim.langsmith_run_id,
            )

        if context.prompt_plan is None:
            raise RuntimeError(
                "run_single_llm_turn requires prompt_plan; "
                "build context via PromptBuilder before invoking AgenticLoop"
            )
        execution = context.execution
        if execution.max_tool_call_rounds == 0:
            sync_result = await _run_chat_only_prompt_plan(
                context,
                llm_client=self.llm_client,
                appender=appender,
            )
        else:
            sync_result = await _run_prompt_plan_tool_loop(
                context,
                store=self.store,
                llm_client=self.llm_client,
                interim_output_sink=(
                    None
                    if execution.suppresses_user_delivery
                    else _emit_user_reply
                ),
                max_tool_call_rounds=execution.max_tool_call_rounds,
            )
        return AgenticLoopOutput(
            assistant_text=sync_result.assistant_text,
            significance_meta=sync_result.significance_meta,
            turn_recall=sync_result.turn_recall,
            langsmith_trace_id=sync_result.langsmith_trace_id,
            langsmith_run_id=sync_result.langsmith_run_id,
            skip_final_transcript_assistant_row=(
                sync_result.skip_final_transcript_assistant_row
            ),
            tool_background_started=False,
            last_interim_assistant_msg_uuid=sync_result.last_interim_assistant_msg_uuid,
            output_message_ids=tuple(appender.persisted_ids),
        )

    async def run_dual_llm_turn(
        self, *, context: AgenticLoopContext
    ) -> AgenticLoopOutput:
        """Execute one dual-LLM turn; foreground and tool-leg user-visible text → ``OutputQueue``."""
        assert (
            context.dual_llm_chat_msgs is not None
            and context.dual_llm_tool_msgs is not None
        )
        _append_user_transcript_row(store=self.store, context=context)
        appender = _UserVisibleOutputAppender(
            output_queue=context.output_queue,
            batch=context.user_message_batch,
            store=self.store,
            image_asset_baseline=len(list_image_asset_records(self.store)),
        )
        llm_client = self.legacy_llm_client
        execution = context.execution
        chat_msgs = list(context.dual_llm_chat_msgs)
        tool_msgs = list(context.dual_llm_tool_msgs)
        apply_agentic_loop_runtime_system_clauses(
            openai_messages=chat_msgs,
            user_text=context.user_text,
        )
        chat_model = llm_client.resolve_model("chat")
        tool_model = llm_client.resolve_model("tool")

        fg_result = await run_dual_llm_foreground_chat(
            DualLlmForegroundChatInput(
                llm_client=llm_client,
                chat_msgs=chat_msgs,
                tool_msgs=tool_msgs,
                chat_model=chat_model,
                langsmith_slice=context.langsmith.turn_slice,
                foreground_scene=execution.llm_scene.value,
                high_reasoning=execution.high_reasoning,
                trace_id=context.trace_id,
                skip_foreground_envelope=execution.skip_foreground_envelope,
                langsmith_trace_id=context.langsmith.trace_id,
                langsmith_run_id=context.langsmith.run_id,
            )
        )
        fg_text = fg_result.assistant_text.strip()
        if fg_text:
            await appender.append_visible_message(
                kind=OutputMessageKind.USER_REPLY,
                text=fg_text,
                trace_id=context.trace_id,
                langsmith_trace_id=fg_result.langsmith_trace_id,
                langsmith_run_id=fg_result.langsmith_run_id,
                turn_recall=fg_result.turn_recall,
            )
        event_sink = _DomainToolBackgroundAppendSink(
            appender=appender,
            trace_id=context.trace_id,
        )

        assert context.companion_turn_track is not None
        await run_tool_background_loop(
            memory_store=self.store,
            request_messages=list(fg_result.tool_msgs_for_bg),
            tool_model=tool_model,
            user_msg_uuid=context.user_msg_uuid,
            trace_id=context.trace_id,
            tools=list(context.openai_tools),
            on_event=event_sink,
            execute_tool_call_fn=execute_tool_call,
            client=llm_client.sync_client_for_route("tool"),
            chat_completion_sync=llm_client.chat_completions_sync,
            write_allowlist=execution.write_allowlist,
            repository_only_store_text=context.repository_only_store_text,
            suppress_user_delivery=execution.suppresses_user_delivery,
            skip_finish_envelope_routing=execution.skip_tool_bg_finish_routing,
            activity_label=execution.tool_bg_activity_label,
            llm_round_timeout_sec=llm_client.config.async_chat_front_timeout_sec,
            runtime_context=context.runtime_context,
            langsmith_slice=context.langsmith.turn_slice,
            companion_turn_track=context.companion_turn_track,
            force_tools_first_round=fg_result.force_tools_first_round,
        )
        await event_sink.flush()
        return AgenticLoopOutput(
            assistant_text=fg_result.assistant_text,
            significance_meta=fg_result.significance_meta,
            turn_recall=fg_result.turn_recall,
            langsmith_trace_id=fg_result.langsmith_trace_id,
            langsmith_run_id=fg_result.langsmith_run_id,
            skip_final_transcript_assistant_row=False,
            tool_background_started=False,
            last_interim_assistant_msg_uuid=None,
            output_message_ids=tuple(appender.persisted_ids),
        )
