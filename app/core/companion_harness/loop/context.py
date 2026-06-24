"""Runtime packaging for production user-turn execution in the agentic loop.

Assembles immutable inputs for one turn (messages, tools, tracing, outbound
queue handles) from values already built upstream. Does not decide prompt
wording or call the language model.
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
from app.core.companion_harness.companion.in_turn_sync_tool_loop import (
    BOOTSTRAP_SYNC_MAX_TOOL_ROUNDS,
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
    InnerTickActivity,
)
from app.core.companion_harness.companion.runtime_channel import (
    TurnRuntimeContext,
)
from app.core.companion_harness.llm.langsmith_invocation_extra import (
    SOURCE_BOOTSTRAP_TRACK,
    SOURCE_FOREGROUND_DUAL_LLM_ENVELOPE,
    SOURCE_SINGLE_COMPLETION,
)
from app.core.companion_harness.prompt_builder import PromptPlan
from app.core.companion_harness.prompting.bundle import PromptBundle
from app.core.companion_harness.tools.companion_tool_definitions import (
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST,
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
)

AfterToolMessagesHook = Callable[
    [list[dict[str, Any]]],
    Awaitable[list[dict[str, Any]] | None],
]


@dataclass(frozen=True)
class AgenticLoopLangsmithContext:
    """Tracing and correlation metadata attached to one agentic loop turn.

    Bundles the slice used for invocation extras plus foreground source label
    and identifiers that tie model calls back to the user message.
    """

    turn_slice: CompanionTurnLangsmithSlice
    foreground_source: str
    trace_id: str
    run_id: str


@dataclass(frozen=True)
class AgenticLoopContext:
    """Everything needed to run one user-facing turn through the agentic loop.

    Built before execution starts: dialogue and tools, transcript targets,
    observability, outbound queue correlation, and optional dual-model message
    stacks or a typed prompt plan. Consumed once per turn by single-LLM or
    dual-LLM loop entry points.
    """

    openai_messages: tuple[dict[str, Any], ...]
    openai_tools: tuple[dict[str, Any], ...]
    write_allowlist: frozenset[str]
    repository_only_store_text: bool
    trace_id: str
    user_text: str
    ts_user: datetime
    user_msg_uuid: str
    # TODO(#3516): Drop legacy scalar tail fields once all loop callers use tail_user_messages only.
    tail_user_messages: tuple[TurnTailUserMessage, ...]
    transcript_rel: str
    langsmith: AgenticLoopLangsmithContext
    inner_tick_turn: bool
    inner_tick_activity: InnerTickActivity
    runtime_context: TurnRuntimeContext
    max_tool_rounds: int
    after_tool_messages_appended: AfterToolMessagesHook | None
    high_reasoning: bool
    output_queue: OutputQueue
    user_message_batch: UserMessageBatch
    context_meta: ContextMeta | None = None
    input_batch: AgenticLoopInputBatch | None = None
    prompt_plan: PromptPlan | None = None
    # TODO(!3460): Migrate 2-LLM message stacks to typed prompt/context; drop legacy dict fields.
    # TODO(!3629): Drop openai_messages once PromptPlan is the sole prompt carrier.
    memory_bootstrap_type: str = ""
    stack_depth: int = 0
    companion_turn_track: CompanionTurnTrack | None = None
    dual_llm_chat_msgs: tuple[dict[str, Any], ...] | None = None
    dual_llm_tool_msgs: tuple[dict[str, Any], ...] | None = None
    prompt_bundle: PromptBundle | None = None
    skip_foreground_envelope: bool = False


@dataclass(frozen=True)
class AgenticLoopOutput:
    """Result summary after one agentic loop turn completes.

    Carries final assistant text, tracing ids, whether a background tool loop
    started, transcript skip hints, and ids of outbound lines persisted during
    the turn for delivery correlation.
    """

    assistant_text: str
    significance_meta: dict[str, Any] | None
    turn_recall: str | None
    langsmith_trace_id: str
    langsmith_run_id: str
    skip_final_transcript_assistant_row: bool
    tool_background_started: bool
    last_interim_assistant_msg_uuid: str | None
    output_message_ids: tuple[str, ...] = ()


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
    memory_bootstrap_type: str,
    stack_depth: int,
    langsmith_trace_id: str,
    langsmith_run_id: str,
    after_tool_messages_appended: AfterToolMessagesHook,
    output_queue: OutputQueue,
    user_message_batch: UserMessageBatch,
    tail_user_messages: tuple[TurnTailUserMessage, ...],
    prompt_plan: PromptPlan | None = None,
) -> AgenticLoopContext:
    """Assemble settled ``USER_CHAT`` context for single-LLM ``AgenticLoop``."""
    assert user_text.strip() != ""
    assert transcript_rel != ""

    return AgenticLoopContext(
        openai_messages=tuple(messages),
        openai_tools=tuple(tools_for_turn),
        write_allowlist=MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST,
        repository_only_store_text=repository_only_store_text,
        trace_id=trace_id,
        user_text=user_text,
        ts_user=ts_user,
        user_msg_uuid=user_msg_uuid,
        transcript_rel=transcript_rel,
        langsmith=AgenticLoopLangsmithContext(
            turn_slice=langsmith_slice,
            foreground_source=SOURCE_SINGLE_COMPLETION,
            trace_id=langsmith_trace_id,
            run_id=langsmith_run_id,
        ),
        inner_tick_turn=False,
        inner_tick_activity=InnerTickActivity.MAINTENANCE,
        runtime_context=runtime_context,
        tail_user_messages=tail_user_messages,
        max_tool_rounds=BOOTSTRAP_SYNC_MAX_TOOL_ROUNDS,
        after_tool_messages_appended=after_tool_messages_appended,
        high_reasoning=False,
        output_queue=output_queue,
        user_message_batch=user_message_batch,
        context_meta=None,
        prompt_plan=prompt_plan,
        memory_bootstrap_type=memory_bootstrap_type,
        stack_depth=stack_depth,
        companion_turn_track=CompanionTurnTrack.USER_CHAT,
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
    memory_bootstrap_type: str,
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
) -> AgenticLoopContext:
    """Assemble settled ``USER_CHAT`` context for dual-LLM ``AgenticLoop``."""
    assert user_text.strip() != ""
    assert transcript_rel != ""
    assert dual_llm_chat_msgs
    assert dual_llm_tool_msgs

    return AgenticLoopContext(
        openai_messages=tuple(messages),
        openai_tools=tuple(tools_for_turn),
        write_allowlist=MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST,
        repository_only_store_text=repository_only_store_text,
        trace_id=trace_id,
        user_text=user_text,
        ts_user=ts_user,
        user_msg_uuid=user_msg_uuid,
        transcript_rel=transcript_rel,
        langsmith=AgenticLoopLangsmithContext(
            turn_slice=langsmith_slice,
            foreground_source=SOURCE_FOREGROUND_DUAL_LLM_ENVELOPE,
            trace_id=langsmith_trace_id,
            run_id=langsmith_run_id,
        ),
        inner_tick_turn=False,
        inner_tick_activity=InnerTickActivity.MAINTENANCE,
        runtime_context=runtime_context,
        tail_user_messages=tail_user_messages,
        max_tool_rounds=BOOTSTRAP_SYNC_MAX_TOOL_ROUNDS,
        after_tool_messages_appended=None,
        high_reasoning=False,
        output_queue=output_queue,
        user_message_batch=user_message_batch,
        context_meta=context_meta,
        memory_bootstrap_type=memory_bootstrap_type,
        stack_depth=stack_depth,
        companion_turn_track=CompanionTurnTrack.USER_CHAT,
        dual_llm_chat_msgs=dual_llm_chat_msgs,
        dual_llm_tool_msgs=dual_llm_tool_msgs,
        prompt_bundle=prompt_bundle,
        skip_foreground_envelope=False,
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
    memory_bootstrap_type: str,
    stack_depth: int,
    langsmith_trace_id: str,
    langsmith_run_id: str,
    after_tool_messages_appended: AfterToolMessagesHook,
    output_queue: OutputQueue,
    user_message_batch: UserMessageBatch,
    tail_user_messages: tuple[TurnTailUserMessage, ...],
    prompt_plan: PromptPlan,
) -> AgenticLoopContext:
    """Assemble bootstrap ``USER_CHAT_BOOTSTRAP`` context for single-LLM ``AgenticLoop``."""
    assert user_text.strip() != ""
    assert transcript_rel != ""

    return AgenticLoopContext(
        openai_messages=tuple(messages),
        openai_tools=tuple(tools_for_turn),
        write_allowlist=MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
        repository_only_store_text=repository_only_store_text,
        trace_id=trace_id,
        user_text=user_text,
        ts_user=ts_user,
        user_msg_uuid=user_msg_uuid,
        transcript_rel=transcript_rel,
        langsmith=AgenticLoopLangsmithContext(
            turn_slice=langsmith_slice,
            foreground_source=SOURCE_BOOTSTRAP_TRACK,
            trace_id=langsmith_trace_id,
            run_id=langsmith_run_id,
        ),
        inner_tick_turn=False,
        inner_tick_activity=InnerTickActivity.MAINTENANCE,
        runtime_context=runtime_context,
        tail_user_messages=tail_user_messages,
        max_tool_rounds=BOOTSTRAP_SYNC_MAX_TOOL_ROUNDS,
        after_tool_messages_appended=after_tool_messages_appended,
        high_reasoning=False,
        output_queue=output_queue,
        user_message_batch=user_message_batch,
        prompt_plan=prompt_plan,
        companion_turn_track=CompanionTurnTrack.USER_CHAT_BOOTSTRAP,
        memory_bootstrap_type=memory_bootstrap_type,
        stack_depth=stack_depth,
    )
