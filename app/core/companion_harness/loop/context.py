"""Runtime packaging for production user-turn execution in the agentic loop.

Assembles immutable inputs for one turn (messages, tools, tracing, outbound
queue handles) from values already built upstream. Does not decide prompt
wording or call the language model.

Per-turn resolved execution knobs are built by ``track_loop_plugin`` via
``build_loop_execution_policy`` and carried on ``AgenticLoopContext.execution``.
``companion_turn_track`` is transcript/logging routing only at loop runtime.

TODO(world-engine-agent-profile): Introduce ``AgentBehavior`` protocol and — #3701
``AgentProfile`` / ``CompanionProfile`` / ``SubAgentProfile`` config (epic #3700).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.core.companion_harness.agentic_companion.output_queue import (
    OutputQueue,
)
from app.core.companion_harness.agentic_companion.types import (
    AgenticLoopInputBatch,
    UserMessageBatch,
)
from app.core.companion_harness.companion.turn_tail_user import (
    TurnTailUserMessage,
)
from app.core.companion_harness.companion.langsmith_turn_slice import (
    CompanionTurnLangsmithSlice,
)
from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    ContextMeta,
)
from app.core.companion_harness.companion.runtime_channel import (
    TurnRuntimeContext,
)
from app.core.companion_harness.loop.track_policy import LoopExecutionPolicy
from app.core.companion_harness.prompt_builder import (
    PromptPlan,
)
from app.core.companion_harness.prompting.bundle import PromptBundle

AfterToolMessagesHook = Callable[
    [list[dict[str, Any]]],
    Awaitable[list[dict[str, Any]] | None],
]


@dataclass(frozen=True)
class AgenticLoopLangsmithContext:
    """Tracing and correlation metadata attached to one agentic loop turn.

    Bundles the slice used for invocation extras plus identifiers that tie
    model calls back to the user message. Foreground LangSmith source labels
    come from ``execution.foreground_source`` on the parent context.
    """

    # Channel tags for LangSmith parent runs and LLM child spans.
    turn_slice: CompanionTurnLangsmithSlice
    # LangSmith trace id for the foreground LLM span on this turn.
    trace_id: str
    # LangSmith run id for the foreground LLM span on this turn.
    run_id: str


@dataclass(frozen=True)
class AgenticLoopContext:
    """Everything needed to run one user-facing turn through the agentic loop.

    Built before execution starts by ``build_*_loop_context`` or ``track_loop_plugin``;
    consumed once per turn by ``AgenticLoop.run_single_llm_turn`` or
    ``AgenticLoop.run_dual_llm_turn``. Execution knobs are pre-resolved on
    ``execution``; loop does not look up ``TRACK_POLICY``.
    """

    # Legacy OpenAI wire message stack from turn prep; single-LLM reads prompt_plan (#3629).
    openai_messages: tuple[dict[str, Any], ...]
    # Tool schemas in OpenAI wire form; dual-LLM background loop reads this, single-LLM uses prompt_plan.tools.
    openai_tools: tuple[dict[str, Any], ...]
    # Production routing track; transcript/logging key only at loop runtime.
    companion_turn_track: CompanionTurnTrack
    # Resolved execution knobs; built by plugin via ``build_loop_execution_policy``.
    execution: LoopExecutionPolicy
    # When true, tool store writes persist text only.
    repository_only_store_text: bool
    # Companion turn correlation id for transcript, OutputQueue, tool events, and logs.
    trace_id: str
    # Primary user-visible utterance; drives reply-language runtime clauses.
    user_text: str
    # UTC timestamp of primary user message; legacy scalar companion to tail_user_messages (#3516).
    ts_user: datetime
    # Primary user message id; assistant transcript reply_to and outbound batch alignment.
    user_msg_uuid: str
    # Tail user rows for prompt assembly and transcript persistence at loop start.
    tail_user_messages: tuple[TurnTailUserMessage, ...]
    # Target transcript JSONL path (e.g. transcript.jsonl).
    transcript_rel: str
    # Foreground LangSmith slice and span ids.
    langsmith: AgenticLoopLangsmithContext
    # Per-turn channel kind and implicit signals; passed to tool background loop.
    runtime_context: TurnRuntimeContext
    # Hook to refresh system prefix after each tool round; None for greeting/inner tick/dual-LLM.
    after_tool_messages_appended: AfterToolMessagesHook | None
    # Durable outbound queue; user-visible assistant lines stream here during the turn.
    output_queue: OutputQueue
    # InputQueue batch claimed for this turn; synthetic for greeting/inner tick without a claim.
    user_message_batch: UserMessageBatch
    # Experience profile and secondary channel context; dual-LLM settled user chat, consumed upstream.
    context_meta: ContextMeta | None = None
    # Ordered InputQueue records for multi-message turns; reserved, not yet passed by builders.
    input_batch: AgenticLoopInputBatch | None = None
    # Primary prompt carrier for single-LLM; required for SINGLE_LLM, absent for dual-LLM user chat.
    prompt_plan: PromptPlan | None = None
    # Leading system message count; used when assembling dual-LLM stacks, not read in loop execution.
    stack_depth: int = 0
    # Dual-LLM foreground chat wire stack; settled USER_CHAT dual-LLM only (#3460).
    dual_llm_chat_msgs: tuple[dict[str, Any], ...] | None = None
    # Dual-LLM background tool wire stack; settled USER_CHAT dual-LLM only (#3460).
    dual_llm_tool_msgs: tuple[dict[str, Any], ...] | None = None
    # Memory-doc bodies for dual-LLM prompt assembly; carried for correlation, consumed upstream.
    prompt_bundle: PromptBundle | None = None


@dataclass(frozen=True)
class AgenticLoopOutput:
    """Result summary after one agentic loop turn completes."""

    # Final assistant body after tool rounds or single completion.
    assistant_text: str
    # Dual-LLM / greeting envelope significance payload when present.
    significance_meta: dict[str, Any] | None
    # Dual-LLM / greeting envelope turn_recall when present.
    turn_recall: str | None
    # Accumulated LangSmith trace id from foreground LLM calls.
    langsmith_trace_id: str
    # Accumulated LangSmith run id from foreground LLM calls.
    langsmith_run_id: str
    # When true, turn end must not append duplicate final assistant row.
    skip_final_transcript_assistant_row: bool
    # True when dual-LLM background tool loop ran.
    tool_background_started: bool
    # Last interim assistant row UUID from in-turn tool loop; None for chat-only tracks.
    last_interim_assistant_msg_uuid: str | None
    # Outbound queue message ids persisted during the turn.
    output_message_ids: tuple[str, ...] = ()


def build_implicit_sign_on_greeting_loop_context(
    *,
    messages: list[dict[str, Any]],
    repository_only_store_text: bool,
    trace_id: str,
    user_text: str,
    ts_user: datetime,
    user_msg_uuid: str,
    transcript_rel: str,
    langsmith_slice: CompanionTurnLangsmithSlice,
    runtime_context: TurnRuntimeContext,
    stack_depth: int,
    langsmith_trace_id: str,
    langsmith_run_id: str,
    output_queue: OutputQueue,
    user_message_batch: UserMessageBatch,
    tail_user_messages: tuple[TurnTailUserMessage, ...],
    prompt_plan: PromptPlan,
    execution: LoopExecutionPolicy,
) -> AgenticLoopContext:
    """Assemble implicit sign-on greeting context for single-LLM ``AgenticLoop``."""
    assert transcript_rel != ""

    return AgenticLoopContext(
        openai_messages=tuple(messages),
        openai_tools=(),
        companion_turn_track=CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING,
        execution=execution,
        repository_only_store_text=repository_only_store_text,
        trace_id=trace_id,
        user_text=user_text,
        ts_user=ts_user,
        user_msg_uuid=user_msg_uuid,
        transcript_rel=transcript_rel,
        langsmith=AgenticLoopLangsmithContext(
            turn_slice=langsmith_slice,
            trace_id=langsmith_trace_id,
            run_id=langsmith_run_id,
        ),
        runtime_context=runtime_context,
        tail_user_messages=tail_user_messages,
        after_tool_messages_appended=None,
        output_queue=output_queue,
        user_message_batch=user_message_batch,
        prompt_plan=prompt_plan,
        stack_depth=stack_depth,
    )


def build_inner_tick_chat_only_loop_context(
    *,
    track: CompanionTurnTrack,
    messages: list[dict[str, Any]],
    repository_only_store_text: bool,
    trace_id: str,
    user_text: str,
    ts_user: datetime,
    user_msg_uuid: str,
    transcript_rel: str,
    langsmith_slice: CompanionTurnLangsmithSlice,
    runtime_context: TurnRuntimeContext,
    stack_depth: int,
    langsmith_trace_id: str,
    langsmith_run_id: str,
    output_queue: OutputQueue,
    user_message_batch: UserMessageBatch,
    tail_user_messages: tuple[TurnTailUserMessage, ...],
    prompt_plan: PromptPlan,
    execution: LoopExecutionPolicy,
) -> AgenticLoopContext:
    """Assemble proactive/scheduled inner-tick context for chat-only ``AgenticLoop``."""
    assert transcript_rel != ""
    assert track in (
        CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT,
        CompanionTurnTrack.INNER_TICK_SCHEDULED,
    )

    return AgenticLoopContext(
        openai_messages=tuple(messages),
        openai_tools=(),
        companion_turn_track=track,
        execution=execution,
        repository_only_store_text=repository_only_store_text,
        trace_id=trace_id,
        user_text=user_text,
        ts_user=ts_user,
        user_msg_uuid=user_msg_uuid,
        transcript_rel=transcript_rel,
        langsmith=AgenticLoopLangsmithContext(
            turn_slice=langsmith_slice,
            trace_id=langsmith_trace_id,
            run_id=langsmith_run_id,
        ),
        runtime_context=runtime_context,
        tail_user_messages=tail_user_messages,
        after_tool_messages_appended=None,
        output_queue=output_queue,
        user_message_batch=user_message_batch,
        prompt_plan=prompt_plan,
        stack_depth=stack_depth,
    )


def build_inner_tick_tool_loop_context(
    *,
    track: CompanionTurnTrack,
    messages: list[dict[str, Any]],
    tools_for_turn: list[dict[str, Any]],
    repository_only_store_text: bool,
    trace_id: str,
    user_text: str,
    ts_user: datetime,
    user_msg_uuid: str,
    transcript_rel: str,
    langsmith_slice: CompanionTurnLangsmithSlice,
    runtime_context: TurnRuntimeContext,
    stack_depth: int,
    langsmith_trace_id: str,
    langsmith_run_id: str,
    output_queue: OutputQueue,
    user_message_batch: UserMessageBatch,
    tail_user_messages: tuple[TurnTailUserMessage, ...],
    prompt_plan: PromptPlan,
    execution: LoopExecutionPolicy,
) -> AgenticLoopContext:
    """Assemble monolog/autonomy inner-tick context for inline tool ``AgenticLoop``."""
    assert transcript_rel != ""
    assert track in (
        CompanionTurnTrack.INNER_TICK_MONOLOG,
        CompanionTurnTrack.INNER_TICK_AUTONOMY,
    )

    return AgenticLoopContext(
        openai_messages=tuple(messages),
        openai_tools=tuple(tools_for_turn),
        companion_turn_track=track,
        execution=execution,
        repository_only_store_text=repository_only_store_text,
        trace_id=trace_id,
        user_text=user_text,
        ts_user=ts_user,
        user_msg_uuid=user_msg_uuid,
        transcript_rel=transcript_rel,
        langsmith=AgenticLoopLangsmithContext(
            turn_slice=langsmith_slice,
            trace_id=langsmith_trace_id,
            run_id=langsmith_run_id,
        ),
        runtime_context=runtime_context,
        tail_user_messages=tail_user_messages,
        after_tool_messages_appended=None,
        output_queue=output_queue,
        user_message_batch=user_message_batch,
        prompt_plan=prompt_plan,
        stack_depth=stack_depth,
    )


def build_settled_user_chat_loop_context(
    *,
    messages: list[dict[str, Any]],
    tools_for_turn: list[dict[str, Any]],
    repository_only_store_text: bool,
    trace_id: str,
    user_text: str,
    ts_user: datetime,
    user_msg_uuid: str,
    transcript_rel: str,
    langsmith_slice: CompanionTurnLangsmithSlice,
    runtime_context: TurnRuntimeContext,
    stack_depth: int,
    langsmith_trace_id: str,
    langsmith_run_id: str,
    after_tool_messages_appended: AfterToolMessagesHook,
    output_queue: OutputQueue,
    user_message_batch: UserMessageBatch,
    tail_user_messages: tuple[TurnTailUserMessage, ...],
    execution: LoopExecutionPolicy,
    prompt_plan: PromptPlan | None = None,
) -> AgenticLoopContext:
    """Assemble settled ``USER_CHAT`` context for single-LLM ``AgenticLoop``."""
    assert user_text.strip() != ""
    assert transcript_rel != ""

    return AgenticLoopContext(
        openai_messages=tuple(messages),
        openai_tools=tuple(tools_for_turn),
        companion_turn_track=CompanionTurnTrack.USER_CHAT,
        execution=execution,
        repository_only_store_text=repository_only_store_text,
        trace_id=trace_id,
        user_text=user_text,
        ts_user=ts_user,
        user_msg_uuid=user_msg_uuid,
        transcript_rel=transcript_rel,
        langsmith=AgenticLoopLangsmithContext(
            turn_slice=langsmith_slice,
            trace_id=langsmith_trace_id,
            run_id=langsmith_run_id,
        ),
        runtime_context=runtime_context,
        tail_user_messages=tail_user_messages,
        after_tool_messages_appended=after_tool_messages_appended,
        output_queue=output_queue,
        user_message_batch=user_message_batch,
        context_meta=None,
        prompt_plan=prompt_plan,
        stack_depth=stack_depth,
    )


def build_settled_dual_llm_user_chat_loop_context(
    *,
    messages: list[dict[str, Any]],
    tools_for_turn: list[dict[str, Any]],
    repository_only_store_text: bool,
    trace_id: str,
    user_text: str,
    ts_user: datetime,
    user_msg_uuid: str,
    transcript_rel: str,
    langsmith_slice: CompanionTurnLangsmithSlice,
    runtime_context: TurnRuntimeContext,
    stack_depth: int,
    langsmith_trace_id: str,
    langsmith_run_id: str,
    output_queue: OutputQueue,
    user_message_batch: UserMessageBatch,
    tail_user_messages: tuple[TurnTailUserMessage, ...],
    dual_llm_chat_msgs: tuple[dict[str, Any], ...],
    dual_llm_tool_msgs: tuple[dict[str, Any], ...],
    prompt_bundle: PromptBundle,
    context_meta: ContextMeta,
    execution: LoopExecutionPolicy,
) -> AgenticLoopContext:
    """Assemble settled ``USER_CHAT`` context for dual-LLM ``AgenticLoop``."""
    assert user_text.strip() != ""
    assert transcript_rel != ""
    assert dual_llm_chat_msgs
    assert dual_llm_tool_msgs

    return AgenticLoopContext(
        openai_messages=tuple(messages),
        openai_tools=tuple(tools_for_turn),
        companion_turn_track=CompanionTurnTrack.USER_CHAT,
        execution=execution,
        repository_only_store_text=repository_only_store_text,
        trace_id=trace_id,
        user_text=user_text,
        ts_user=ts_user,
        user_msg_uuid=user_msg_uuid,
        transcript_rel=transcript_rel,
        langsmith=AgenticLoopLangsmithContext(
            turn_slice=langsmith_slice,
            trace_id=langsmith_trace_id,
            run_id=langsmith_run_id,
        ),
        runtime_context=runtime_context,
        tail_user_messages=tail_user_messages,
        after_tool_messages_appended=None,
        output_queue=output_queue,
        user_message_batch=user_message_batch,
        context_meta=context_meta,
        stack_depth=stack_depth,
        dual_llm_chat_msgs=dual_llm_chat_msgs,
        dual_llm_tool_msgs=dual_llm_tool_msgs,
        prompt_bundle=prompt_bundle,
    )


def build_bootstrap_user_chat_loop_context(
    *,
    messages: list[dict[str, Any]],
    tools_for_turn: list[dict[str, Any]],
    repository_only_store_text: bool,
    trace_id: str,
    user_text: str,
    ts_user: datetime,
    user_msg_uuid: str,
    transcript_rel: str,
    langsmith_slice: CompanionTurnLangsmithSlice,
    runtime_context: TurnRuntimeContext,
    stack_depth: int,
    langsmith_trace_id: str,
    langsmith_run_id: str,
    after_tool_messages_appended: AfterToolMessagesHook,
    output_queue: OutputQueue,
    user_message_batch: UserMessageBatch,
    tail_user_messages: tuple[TurnTailUserMessage, ...],
    prompt_plan: PromptPlan,
    execution: LoopExecutionPolicy,
) -> AgenticLoopContext:
    """Assemble bootstrap ``USER_CHAT_BOOTSTRAP`` context for single-LLM ``AgenticLoop``."""
    assert user_text.strip() != ""
    assert transcript_rel != ""

    return AgenticLoopContext(
        openai_messages=tuple(messages),
        openai_tools=tuple(tools_for_turn),
        companion_turn_track=CompanionTurnTrack.USER_CHAT_BOOTSTRAP,
        execution=execution,
        repository_only_store_text=repository_only_store_text,
        trace_id=trace_id,
        user_text=user_text,
        ts_user=ts_user,
        user_msg_uuid=user_msg_uuid,
        transcript_rel=transcript_rel,
        langsmith=AgenticLoopLangsmithContext(
            turn_slice=langsmith_slice,
            trace_id=langsmith_trace_id,
            run_id=langsmith_run_id,
        ),
        runtime_context=runtime_context,
        tail_user_messages=tail_user_messages,
        after_tool_messages_appended=after_tool_messages_appended,
        output_queue=output_queue,
        user_message_batch=user_message_batch,
        prompt_plan=prompt_plan,
        stack_depth=stack_depth,
    )
