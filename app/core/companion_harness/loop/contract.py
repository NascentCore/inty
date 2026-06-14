"""Agentic loop interchange contract: one Input, one Output, one Mechanism protocol."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from app.core.companion_harness.companion.langsmith_turn_slice import (
    CompanionTurnLangsmithSlice,
)
from app.core.companion_harness.companion.llm_client import CompanionLLMClient
from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    ContextMeta,
    InnerTickActivity,
)
from app.core.companion_harness.companion.runtime_channel import TurnRuntimeContext
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.prompting.bundle import PromptBundle

from .output_queue import AgenticLoopOutputQueue, LoopDeliverable


AfterToolMessagesHook = Callable[
    [list[dict[str, Any]]],
    Awaitable[tuple[dict[str, Any], ...] | None],
]


@dataclass(frozen=True)
class AgenticLoopInput:
    """Mode-agnostic superset input for ``run_agentic_loop`` (swap ``llm_loop_mode`` only)."""

    store: MemoryStore
    llm_client: CompanionLLMClient
    openai_messages: tuple[dict[str, Any], ...]
    openai_tools: tuple[dict[str, Any], ...]
    write_allowlist: frozenset[str]
    repository_only_store_text: bool
    trace_id: str
    user_text: str
    ts_user: datetime
    user_msg_uuid: str
    transcript_rel: str
    langsmith_slice: CompanionTurnLangsmithSlice
    companion_turn_track: CompanionTurnTrack
    inner_tick_turn: bool
    inner_tick_activity: InnerTickActivity
    runtime_context: TurnRuntimeContext
    langsmith_foreground_source: str
    max_tool_rounds: int
    after_tool_messages_appended: AfterToolMessagesHook | None
    memory_bootstrap_type: str
    stack_depth: int
    skip_foreground_envelope: bool
    high_reasoning: bool
    langsmith_trace_id: str
    langsmith_run_id: str
    prompt_bundle: PromptBundle | None
    context_meta: ContextMeta | None
    dual_llm_chat_msgs: tuple[dict[str, Any], ...] | None
    dual_llm_tool_msgs: tuple[dict[str, Any], ...] | None


@dataclass(frozen=True)
class AgenticLoopRunBundle:
    """``AgenticLoopInput`` plus injected per-call-streaming queue."""

    loop_input: AgenticLoopInput
    output_queue: AgenticLoopOutputQueue


@dataclass(frozen=True)
class AgenticLoopOutput:
    """Turn summary returned when the agentic loop finishes (UX uses channel per-call-streaming)."""

    assistant_text: str
    significance_meta: dict[str, Any] | None
    turn_recall: str | None
    langsmith_trace_id: str
    langsmith_run_id: str
    deliverables: tuple[LoopDeliverable, ...]
    skip_final_transcript_assistant_row: bool
    tool_background_started: bool
    last_interim_assistant_msg_uuid: str | None


class AgenticLoopMechanism(Protocol):
    """Interchangeable 1-LLM / 2-LLM loop implementation."""

    async def run(self, bundle: AgenticLoopRunBundle) -> AgenticLoopOutput:
        """Execute one agentic loop; per-call deliverables via ``bundle.output_queue``."""


def agentic_loop_run_bundle(
    loop_input: AgenticLoopInput,
    output_queue: AgenticLoopOutputQueue,
) -> AgenticLoopRunBundle:
    """Attach ``output_queue`` for mechanism execution."""
    return AgenticLoopRunBundle(
        loop_input=loop_input,
        output_queue=output_queue,
    )
