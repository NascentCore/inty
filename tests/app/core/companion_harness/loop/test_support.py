"""Shared test helpers for legacy agentic loop sidecar tests (``test_support`` consumers).

For ``loop/context.py`` builder kwargs, use ``context_builder_test_support`` instead.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.companion_harness.companion.langsmith_turn_slice import (
    CompanionTurnLangsmithSlice,
)
from app.core.companion_harness.companion.llm_client import CompanionLLMClient
from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    InnerTickActivity,
)
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
    TurnRuntimeContext,
)
from app.core.companion_harness.llm.langsmith_invocation_extra import (
    SOURCE_BOOTSTRAP_TRACK,
)
from app.core.companion_harness.loop.contract import LegacyAgenticLoopContext
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.tools.companion_tool_definitions import (
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
)


def default_runtime_context() -> TurnRuntimeContext:
    return TurnRuntimeContext(
        channel=CompanionRuntimeChannel.APP,
        implicit_signal_bundle=None,
    )


def default_langsmith_slice() -> CompanionTurnLangsmithSlice:
    return CompanionTurnLangsmithSlice.from_runtime_context(
        default_runtime_context()
    )


def build_agentic_loop_input(
    *,
    store: MemoryStore,
    llm_client: CompanionLLMClient,
    openai_messages: tuple[dict[str, Any], ...],
    openai_tools: tuple[dict[str, Any], ...],
    user_text: str,
    user_msg_uuid: str,
    trace_id: str,
    write_allowlist: frozenset[str] = MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
    langsmith_foreground_source: str = SOURCE_BOOTSTRAP_TRACK,
    max_tool_rounds: int = 4,
    skip_foreground_envelope: bool = False,
    high_reasoning: bool = False,
    dual_llm_chat_msgs: tuple[dict[str, Any], ...] | None = None,
    dual_llm_tool_msgs: tuple[dict[str, Any], ...] | None = None,
) -> LegacyAgenticLoopContext:
    """Build a mode-agnostic legacy loop context for sidecar tests."""
    return LegacyAgenticLoopContext(
        store=store,
        llm_client=llm_client,
        openai_messages=openai_messages,
        openai_tools=openai_tools,
        write_allowlist=write_allowlist,
        repository_only_store_text=False,
        trace_id=trace_id,
        user_text=user_text,
        ts_user=datetime(2026, 1, 1, tzinfo=timezone.utc),
        user_msg_uuid=user_msg_uuid,
        transcript_rel="transcript.jsonl",
        langsmith_slice=default_langsmith_slice(),
        companion_turn_track=CompanionTurnTrack.USER_CHAT_BOOTSTRAP,
        inner_tick_turn=False,
        inner_tick_activity=InnerTickActivity.MAINTENANCE,
        runtime_context=default_runtime_context(),
        langsmith_foreground_source=langsmith_foreground_source,
        max_tool_rounds=max_tool_rounds,
        after_tool_messages_appended=None,
        memory_bootstrap_type="none",
        stack_depth=0,
        skip_foreground_envelope=skip_foreground_envelope,
        high_reasoning=high_reasoning,
        langsmith_trace_id="",
        langsmith_run_id="",
        prompt_bundle=None,
        context_meta=None,
        dual_llm_chat_msgs=dual_llm_chat_msgs,
        dual_llm_tool_msgs=dual_llm_tool_msgs,
    )
