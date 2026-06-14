"""Build ``AgenticLoopInput`` for settled ``USER_CHAT`` dual-LLM track."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

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
from app.core.companion_harness.loop.contract import AgenticLoopInput
from app.core.companion_harness.tools.companion_tool_definitions import (
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST,
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_AUTONOMY,
)


@dataclass(frozen=True)
class SettledAgenticLoopBuildInput:
    """Facts available in ``turn.py`` settled dual-LLM branch."""

    store: MemoryStore
    llm_client: CompanionLLMClient
    openai_messages: tuple[dict[str, Any], ...]
    openai_tools: tuple[dict[str, Any], ...]
    dual_llm_chat_msgs: tuple[dict[str, Any], ...]
    dual_llm_tool_msgs: tuple[dict[str, Any], ...]
    companion_turn_track: CompanionTurnTrack
    memory_bootstrap_type: str
    repository_only_store_text: bool
    trace_id: str
    user_text: str
    ts_user: datetime
    user_msg_uuid: str
    transcript_rel: str
    langsmith_slice: CompanionTurnLangsmithSlice
    runtime_context: TurnRuntimeContext
    inner_tick_turn: bool
    inner_tick_activity: InnerTickActivity
    skip_foreground_envelope: bool
    high_reasoning: bool
    langsmith_trace_id: str
    langsmith_run_id: str
    prompt_bundle: PromptBundle | None
    context_meta: ContextMeta | None
    stack_depth: int


def _write_allowlist_for_track(track: CompanionTurnTrack) -> frozenset[str]:
    # TODO: dedupe with ``turn._memory_store_write_allowlist_for_track`` (#3398 loop cleanup).
    match track:
        case CompanionTurnTrack.INNER_TICK_AUTONOMY:
            return MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_AUTONOMY
        case CompanionTurnTrack.INNER_TICK_MAINTENANCE:
            return frozenset()
        case _:
            return MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST


def build_settled_agentic_loop_input(
    build_input: SettledAgenticLoopBuildInput,
) -> AgenticLoopInput:
    """Map settled turn state to ``AgenticLoopInput`` for ``DUAL_LLM``."""
    return AgenticLoopInput(
        store=build_input.store,
        llm_client=build_input.llm_client,
        openai_messages=build_input.openai_messages,
        openai_tools=build_input.openai_tools,
        write_allowlist=_write_allowlist_for_track(build_input.companion_turn_track),
        repository_only_store_text=build_input.repository_only_store_text,
        trace_id=build_input.trace_id,
        user_text=build_input.user_text,
        ts_user=build_input.ts_user,
        user_msg_uuid=build_input.user_msg_uuid,
        transcript_rel=build_input.transcript_rel,
        langsmith_slice=build_input.langsmith_slice,
        companion_turn_track=build_input.companion_turn_track,
        inner_tick_turn=build_input.inner_tick_turn,
        inner_tick_activity=build_input.inner_tick_activity,
        runtime_context=build_input.runtime_context,
        langsmith_foreground_source="",
        max_tool_rounds=0,
        after_tool_messages_appended=None,
        memory_bootstrap_type=build_input.memory_bootstrap_type,
        stack_depth=build_input.stack_depth,
        skip_foreground_envelope=build_input.skip_foreground_envelope,
        high_reasoning=build_input.high_reasoning,
        langsmith_trace_id=build_input.langsmith_trace_id,
        langsmith_run_id=build_input.langsmith_run_id,
        prompt_bundle=build_input.prompt_bundle,
        context_meta=build_input.context_meta,
        dual_llm_chat_msgs=build_input.dual_llm_chat_msgs,
        dual_llm_tool_msgs=build_input.dual_llm_tool_msgs,
    )
