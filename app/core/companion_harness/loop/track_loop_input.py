"""Prepared per-turn state handed from turn.py to an AgenticLoop turn plugin."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.core.companion_harness.agentic_companion.output_queue import (
    OutputQueue,
)
from app.core.companion_harness.agentic_companion.types import (
    UserMessageBatch,
)
from app.core.companion_harness.companion.langsmith_turn_slice import (
    CompanionTurnLangsmithSlice,
)
from app.core.companion_harness.companion.models import CompanionTurnTrack
from app.core.companion_harness.companion.runtime_channel import (
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.transcript_ai_private import (
    AiPrivateSplicePlan,
)
from app.core.companion_harness.companion.turn_pipeline import (
    CompanionTurnLoadedState,
    CompanionTurnPromptPlan,
    CompanionTurnRuntimeFlags,
)
from app.core.companion_harness.companion.turn_tail_user import (
    TurnTailUserMessage,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.llms.client import LlmClient


@dataclass(frozen=True)
class CompanionTurnLoopInput:
    """Loop-stage inputs assembled after turn prep and before AgenticLoop dispatch."""

    store: MemoryStore
    llm_client: LlmClient
    track: CompanionTurnTrack
    runtime_flags: CompanionTurnRuntimeFlags
    loaded_state: CompanionTurnLoadedState
    prompt_plan: CompanionTurnPromptPlan
    tail_user_messages: tuple[TurnTailUserMessage, ...]
    messages: list[dict[str, Any]]
    tools_for_turn: list[dict[str, Any]]
    trace_id: str
    langsmith_slice: CompanionTurnLangsmithSlice
    runtime_context: TurnRuntimeContext
    agentic_output_queue: OutputQueue
    user_message_batch: UserMessageBatch | None
    user_text: str
    ts_user: datetime
    user_msg_uuid: str
    ai_private_splice_plan: AiPrivateSplicePlan
    repository_only_store_text: bool
    langsmith_trace_id: str
    langsmith_run_id: str
    transcript_rel: str
