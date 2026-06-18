"""Golden scenario builders for loop sidecar parity (fake LLM, no network)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from app.core.companion_harness.companion.langsmith_turn_slice import (
    CompanionTurnLangsmithSlice,
)
from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    InnerTickActivity,
)
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.llm.langsmith_invocation_extra import (
    SOURCE_BOOTSTRAP_TRACK,
)
from app.core.companion_harness.loop.contract import LegacyAgenticLoopContext
from app.core.companion_harness.loop.parity.fixtures import (
    FakeDualLlmClient,
    FakeSyncToolLoopLLMClient,
    dual_llm_fg_response,
    dual_llm_tool_finish_response,
    final_response,
    tool_response,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.tools.companion_tool_definitions import (
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
)


class GoldenScenario(StrEnum):
    """Named parity scenarios from sidecar plan."""

    BOOTSTRAP_SYNC_INTERIM = "bootstrap_sync_interim"
    TOOL_FEEDBACK_TERMINAL = "tool_feedback_terminal"
    DUAL_LLM_FG_THEN_TOOL = "dual_llm_fg_then_tool"
    MAINTENANCE_SKIP_FG = "maintenance_skip_fg"


@dataclass(frozen=True)
class GoldenScenarioBundle:
    """One golden scenario: store, fake client, and legacy loop context."""

    store: MemoryStore
    llm_client: FakeSyncToolLoopLLMClient | FakeDualLlmClient
    loop_context: LegacyAgenticLoopContext
    expected_mode: str


def _runtime_context() -> TurnRuntimeContext:
    return TurnRuntimeContext(
        channel=CompanionRuntimeChannel.APP,
        implicit_signal_bundle=None,
    )


def _langsmith_slice() -> CompanionTurnLangsmithSlice:
    return CompanionTurnLangsmithSlice.from_runtime_context(_runtime_context())


def _memory_write_tool() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "memory_store_write_document",
            "parameters": {"type": "object", "properties": {}},
        },
    }


def _base_loop_input(
    *,
    store: MemoryStore,
    llm_client: FakeSyncToolLoopLLMClient | FakeDualLlmClient,
    openai_messages: tuple[dict[str, Any], ...],
    openai_tools: tuple[dict[str, Any], ...],
    user_text: str,
    user_msg_uuid: str,
    trace_id: str,
    skip_foreground_envelope: bool,
    dual_llm_chat_msgs: tuple[dict[str, Any], ...] | None,
    dual_llm_tool_msgs: tuple[dict[str, Any], ...] | None,
) -> LegacyAgenticLoopContext:
    return LegacyAgenticLoopContext(
        store=store,
        llm_client=llm_client,  # type: ignore[arg-type]
        openai_messages=openai_messages,
        openai_tools=openai_tools,
        write_allowlist=MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
        repository_only_store_text=False,
        trace_id=trace_id,
        user_text=user_text,
        ts_user=datetime(2026, 1, 1, tzinfo=timezone.utc),
        user_msg_uuid=user_msg_uuid,
        transcript_rel="transcript.jsonl",
        langsmith_slice=_langsmith_slice(),
        companion_turn_track=CompanionTurnTrack.USER_CHAT_BOOTSTRAP,
        inner_tick_turn=False,
        inner_tick_activity=InnerTickActivity.MAINTENANCE,
        runtime_context=_runtime_context(),
        langsmith_foreground_source=SOURCE_BOOTSTRAP_TRACK,
        max_tool_rounds=4,
        after_tool_messages_appended=None,
        memory_bootstrap_type="none",
        stack_depth=0,
        skip_foreground_envelope=skip_foreground_envelope,
        high_reasoning=False,
        langsmith_trace_id="",
        langsmith_run_id="",
        prompt_bundle=None,
        context_meta=None,
        dual_llm_chat_msgs=dual_llm_chat_msgs,
        dual_llm_tool_msgs=dual_llm_tool_msgs,
    )


def _fresh_store(*, label: str) -> MemoryStore:
    store = MemoryStore(
        scope=CompanionScope("loop-golden", "agent", label),
        repository=None,
    )
    store.write_document("transcript.jsonl", "")
    return store


def build_golden_scenario(scenario: GoldenScenario) -> GoldenScenarioBundle:
    """Build store, fake client, and input for one golden scenario."""
    match scenario:
        case GoldenScenario.BOOTSTRAP_SYNC_INTERIM:
            store = _fresh_store(label="bootstrap-interim")
            store.write_document("IDENTITY.md", "IDENTITY\n")
            client = FakeSyncToolLoopLLMClient(
                [
                    tool_response(
                        content="interim",
                        tool_name="memory_store_write_document",
                        tool_arguments=json.dumps(
                            {"relative_path": "IDENTITY.md", "content": "x\n"},
                            ensure_ascii=False,
                        ),
                    ),
                    final_response(content="terminal"),
                ]
            )
            msgs = ({"role": "user", "content": "go"},)
            loop_context = _base_loop_input(
                store=store,
                llm_client=client,
                openai_messages=msgs,
                openai_tools=(_memory_write_tool(),),
                user_text="go",
                user_msg_uuid="golden-interim-user",
                trace_id="golden-interim-trace",
                skip_foreground_envelope=False,
                dual_llm_chat_msgs=None,
                dual_llm_tool_msgs=None,
            )
            return GoldenScenarioBundle(
                store=store,
                llm_client=client,
                loop_context=loop_context,
                expected_mode="in_turn_single_llm",
            )
        case GoldenScenario.TOOL_FEEDBACK_TERMINAL:
            store = _fresh_store(label="tool-feedback")
            client = FakeSyncToolLoopLLMClient(
                [final_response(content="smoke ok")]
            )
            msgs = ({"role": "user", "content": "feedback"},)
            loop_context = _base_loop_input(
                store=store,
                llm_client=client,
                openai_messages=msgs,
                openai_tools=(),
                user_text="feedback",
                user_msg_uuid="golden-feedback-user",
                trace_id="golden-feedback-trace",
                skip_foreground_envelope=False,
                dual_llm_chat_msgs=None,
                dual_llm_tool_msgs=None,
            )
            return GoldenScenarioBundle(
                store=store,
                llm_client=client,
                loop_context=loop_context,
                expected_mode="in_turn_single_llm",
            )
        case GoldenScenario.DUAL_LLM_FG_THEN_TOOL:
            store = _fresh_store(label="dual-fg-tool")
            msgs = ({"role": "user", "content": "hi"},)

            def _tool_sync(*_args: object, **_kwargs: object) -> object:
                return dual_llm_tool_finish_response()

            client = FakeDualLlmClient(
                fg_response=dual_llm_fg_response(text="foreground ok"),
                tool_sync_handler=_tool_sync,
            )
            loop_context = _base_loop_input(
                store=store,
                llm_client=client,
                openai_messages=msgs,
                openai_tools=(),
                user_text="hi",
                user_msg_uuid="golden-fg-user",
                trace_id="golden-fg-trace",
                skip_foreground_envelope=False,
                dual_llm_chat_msgs=msgs,
                dual_llm_tool_msgs=msgs,
            )
            return GoldenScenarioBundle(
                store=store,
                llm_client=client,
                loop_context=loop_context,
                expected_mode="dual_llm",
            )
        case GoldenScenario.MAINTENANCE_SKIP_FG:
            store = _fresh_store(label="maint-skip-fg")
            msgs = ({"role": "user", "content": "maint"},)

            def _tool_sync(*_args: object, **_kwargs: object) -> object:
                return dual_llm_tool_finish_response()

            client = FakeDualLlmClient(
                fg_response=dual_llm_fg_response(text="unused"),
                tool_sync_handler=_tool_sync,
            )
            loop_context = _base_loop_input(
                store=store,
                llm_client=client,
                openai_messages=msgs,
                openai_tools=(),
                user_text="maint",
                user_msg_uuid="golden-maint-user",
                trace_id="golden-maint-trace",
                skip_foreground_envelope=True,
                dual_llm_chat_msgs=msgs,
                dual_llm_tool_msgs=msgs,
            )
            return GoldenScenarioBundle(
                store=store,
                llm_client=client,
                loop_context=loop_context,
                expected_mode="dual_llm",
            )
        case _:
            raise AssertionError(f"unknown golden scenario: {scenario}")
