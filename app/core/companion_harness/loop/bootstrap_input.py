"""Build ``AgenticLoopInput`` for bootstrap ``USER_CHAT_BOOTSTRAP`` track."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.core.companion_harness.companion.in_turn_sync_tool_loop import (
    BOOTSTRAP_SYNC_MAX_TOOL_ROUNDS,
)
from app.core.companion_harness.companion.langsmith_turn_slice import (
    CompanionTurnLangsmithSlice,
)
from app.core.companion_harness.companion.llm_client import CompanionLLMClient
from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    InnerTickActivity,
)
from app.core.companion_harness.companion.runtime_channel import TurnRuntimeContext
from app.core.companion_harness.llm.langsmith_invocation_extra import (
    SOURCE_BOOTSTRAP_TRACK,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.companion.prompt_stack import (
    refresh_companion_turn_prompt_stack,
)
from app.core.companion_harness.loop.contract import (
    AfterToolMessagesHook,
    AgenticLoopInput,
)
from app.core.companion_harness.tools.companion_tool_definitions import (
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
)


@dataclass(frozen=True)
class BootstrapAgenticLoopBuildInput:
    """Facts available in ``turn.py`` bootstrap branch."""

    store: MemoryStore
    llm_client: CompanionLLMClient
    openai_messages: tuple[dict[str, Any], ...]
    openai_tools: tuple[dict[str, Any], ...]
    memory_bootstrap_type: str
    repository_only_store_text: bool
    trace_id: str
    user_text: str
    ts_user: datetime
    user_msg_uuid: str
    transcript_rel: str
    langsmith_slice: CompanionTurnLangsmithSlice
    runtime_context: TurnRuntimeContext


def build_bootstrap_agentic_loop_input(
    build_input: BootstrapAgenticLoopBuildInput,
) -> AgenticLoopInput:
    """Map bootstrap turn state to ``AgenticLoopInput`` for ``IN_TURN_SINGLE_LLM``."""
    store = build_input.store
    memory_bootstrap_type = build_input.memory_bootstrap_type

    async def _after_tool_round(
        messages_with_tool_results: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], ...] | None:
        refreshed = refresh_companion_turn_prompt_stack(
            store=store,
            memory_bootstrap_type=memory_bootstrap_type,
            inner_tick_turn=False,
            inner_tick_activity=InnerTickActivity.MAINTENANCE,
            messages=messages_with_tool_results,
            track=CompanionTurnTrack.USER_CHAT_BOOTSTRAP,
        )
        return tuple(refreshed)

    hook: AfterToolMessagesHook = _after_tool_round
    return AgenticLoopInput(
        store=store,
        llm_client=build_input.llm_client,
        openai_messages=build_input.openai_messages,
        openai_tools=build_input.openai_tools,
        write_allowlist=MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
        repository_only_store_text=build_input.repository_only_store_text,
        trace_id=build_input.trace_id,
        user_text=build_input.user_text,
        ts_user=build_input.ts_user,
        user_msg_uuid=build_input.user_msg_uuid,
        transcript_rel=build_input.transcript_rel,
        langsmith_slice=build_input.langsmith_slice,
        companion_turn_track=CompanionTurnTrack.USER_CHAT_BOOTSTRAP,
        inner_tick_turn=False,
        inner_tick_activity=InnerTickActivity.MAINTENANCE,
        runtime_context=build_input.runtime_context,
        langsmith_foreground_source=SOURCE_BOOTSTRAP_TRACK,
        max_tool_rounds=BOOTSTRAP_SYNC_MAX_TOOL_ROUNDS,
        after_tool_messages_appended=hook,
        memory_bootstrap_type=memory_bootstrap_type,
        stack_depth=0,
        skip_foreground_envelope=False,
        high_reasoning=False,
        langsmith_trace_id="",
        langsmith_run_id="",
        prompt_bundle=None,
        context_meta=None,
        dual_llm_chat_msgs=None,
        dual_llm_tool_msgs=None,
    )
