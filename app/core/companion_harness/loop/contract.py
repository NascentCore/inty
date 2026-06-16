"""Agentic loop interchange contract: legacy mechanism protocol and re-exports.

TODO(#3460): Delete legacy mechanism contract types from this module after
dead-code cleanup; production types live in loop/context.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from app.core.companion_harness.agentic_companion.types import (
    AgenticLoopInputBatch,
)
from app.core.companion_harness.companion.langsmith_turn_slice import (
    CompanionTurnLangsmithSlice,
)
from app.core.companion_harness.companion.llm_client import CompanionLLMClient
from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    ContextMeta,
    InnerTickActivity,
)
from app.core.companion_harness.companion.runtime_channel import (
    TurnRuntimeContext,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.prompting.bundle import PromptBundle

from .context import (
    AfterToolMessagesHook,
    AgenticLoopOutput,
)
from .output_queue import AgenticLoopOutputSink


# TODO(#3460): Delete this after direct AgenticLoop user-turn methods retire the
# legacy channel runner and 2-LLM parity harness.
@dataclass(frozen=True)
class LegacyAgenticLoopContext:
    """Legacy parity context without domain ``OutputQueue`` (channel runner only)."""

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
    input_batch: AgenticLoopInputBatch | None = None


@dataclass(frozen=True)
class AgenticLoopRunBundle:
    """Legacy context plus injected per-call-streaming queue."""

    loop_context: LegacyAgenticLoopContext
    output_queue: AgenticLoopOutputSink


class AgenticLoopMechanism(Protocol):
    """Legacy interchangeable 1-LLM / 2-LLM loop implementation."""

    async def run(self, bundle: AgenticLoopRunBundle) -> AgenticLoopOutput:
        """Execute one agentic loop; per-call deliverables via ``bundle.output_queue``."""


def agentic_loop_run_bundle(
    loop_context: LegacyAgenticLoopContext,
    output_queue: AgenticLoopOutputSink,
) -> AgenticLoopRunBundle:
    """Attach ``output_queue`` for legacy mechanism execution."""
    return AgenticLoopRunBundle(
        loop_context=loop_context,
        output_queue=output_queue,
    )
