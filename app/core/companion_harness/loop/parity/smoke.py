"""Parity smoke CLI for agentic loop sidecar."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from enum import StrEnum

import cyclopts

from app.core.companion_harness.companion.in_turn_sync_tool_loop import (
    BootstrapInTurnSyncToolLoopInput,
    run_bootstrap_track_sync_tool_loop,
)
from app.core.companion_harness.companion.langsmith_turn_slice import (
    CompanionTurnLangsmithSlice,
)
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.loop.channel_adapter import RecordingChannelAdapter
from app.core.companion_harness.loop.config import UserTurnLlmLoopMode
from app.core.companion_harness.loop.parity.golden import (
    GoldenScenario,
    build_golden_scenario,
)
from app.core.companion_harness.loop.runner import run_agentic_loop
from app.core.companion_harness.memory.memory_store import MemoryStore


class SmokeScenario(StrEnum):
    """CLI scenario names (subset of ``GoldenScenario``)."""

    TOOL_FEEDBACK = "tool_feedback"


app = cyclopts.App(
    name="agentic-loop-parity-smoke",
    help="Sidecar agentic loop parity smoke (fake LLM).",
)


def _golden_for_smoke(scenario: SmokeScenario) -> GoldenScenario:
    match scenario:
        case SmokeScenario.TOOL_FEEDBACK:
            return GoldenScenario.TOOL_FEEDBACK_TERMINAL
        case _:
            raise AssertionError(f"unknown smoke scenario: {scenario}")


@app.command
def run(
    scenario: SmokeScenario,
    mode: UserTurnLlmLoopMode,
) -> None:
    """Run one sidecar scenario with fake LLM."""
    asyncio.run(_run_scenario(scenario=scenario, mode=mode))


@app.command
def compare_legacy(scenario: SmokeScenario) -> None:
    """Compare sidecar 1-LLM output shape vs direct bootstrap wrapper (smoke)."""
    asyncio.run(_compare_legacy(scenario=scenario))


async def _run_scenario(
    *,
    scenario: SmokeScenario,
    mode: UserTurnLlmLoopMode,
) -> None:
    golden = _golden_for_smoke(scenario)
    bundle = build_golden_scenario(golden)
    channel = RecordingChannelAdapter()
    result = await run_agentic_loop(
        bundle.loop_input,
        llm_loop_mode=mode,
        channel=channel,
    )
    print(
        json.dumps(
            {
                "scenario": scenario.value,
                "mode": mode.value,
                "assistant_text": result.assistant_text,
                "deliverables_n": len(result.deliverables),
                "channel_events_n": len(channel.events),
            },
            ensure_ascii=False,
        )
    )


async def _compare_legacy(scenario: SmokeScenario) -> None:
    golden = _golden_for_smoke(scenario)
    bundle = build_golden_scenario(golden)
    channel = RecordingChannelAdapter()
    sidecar = await run_agentic_loop(
        bundle.loop_input,
        llm_loop_mode=UserTurnLlmLoopMode.IN_TURN_SINGLE_LLM,
        channel=channel,
    )
    legacy_store = MemoryStore(
        scope=CompanionScope("smoke-legacy-run", "agent", "loop-legacy-run"),
        repository=None,
    )
    legacy_store.write_document("transcript.jsonl", "")
    legacy_bundle = build_golden_scenario(golden)
    legacy = await run_bootstrap_track_sync_tool_loop(
        BootstrapInTurnSyncToolLoopInput(
            store=legacy_store,
            llm_client=legacy_bundle.llm_client,  # type: ignore[arg-type]
            messages=legacy_bundle.loop_input.openai_messages,
            tools_for_turn=legacy_bundle.loop_input.openai_tools,
            memory_bootstrap_type="none",
            repository_only_store_text=False,
            trace_id=legacy_bundle.loop_input.trace_id,
            user_text=legacy_bundle.loop_input.user_text,
            ts_user=datetime(2026, 1, 1, tzinfo=timezone.utc),
            user_msg_uuid=legacy_bundle.loop_input.user_msg_uuid,
            transcript_rel=legacy_bundle.loop_input.transcript_rel,
            bootstrap_interim_output_sink=None,
            langsmith_slice=CompanionTurnLangsmithSlice.from_runtime_context(
                TurnRuntimeContext(
                    channel=CompanionRuntimeChannel.APP,
                    implicit_signal_bundle=None,
                )
            ),
        )
    )
    print(
        json.dumps(
            {
                "scenario": scenario.value,
                "sidecar_assistant_text": sidecar.assistant_text,
                "legacy_assistant_text": legacy.assistant_text,
                "text_match": sidecar.assistant_text == legacy.assistant_text,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    app()
