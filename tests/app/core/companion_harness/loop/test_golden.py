"""Golden scenario smoke: all four plan scenarios run through ``run_agentic_loop``."""

from __future__ import annotations

import pytest

from app.core.companion_harness.loop.channel_adapter import RecordingChannelAdapter
from app.core.companion_harness.loop.config import UserTurnLlmLoopMode
from app.core.companion_harness.loop.parity.golden import (
    GoldenScenario,
    build_golden_scenario,
)
from app.core.companion_harness.loop.runner import run_agentic_loop


def _mode_for(scenario: GoldenScenario) -> UserTurnLlmLoopMode:
    match scenario:
        case (
            GoldenScenario.BOOTSTRAP_SYNC_INTERIM
            | GoldenScenario.TOOL_FEEDBACK_TERMINAL
        ):
            return UserTurnLlmLoopMode.IN_TURN_SINGLE_LLM
        case GoldenScenario.DUAL_LLM_FG_THEN_TOOL | GoldenScenario.MAINTENANCE_SKIP_FG:
            return UserTurnLlmLoopMode.DUAL_LLM
        case _:
            raise AssertionError(f"unknown scenario: {scenario}")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario",
    list(GoldenScenario),
)
async def test_golden_scenario_runs(scenario: GoldenScenario) -> None:
    bundle = build_golden_scenario(scenario)
    channel = RecordingChannelAdapter()
    result = await run_agentic_loop(
        bundle.loop_context,
        llm_loop_mode=_mode_for(scenario),
        channel=channel,
    )
    assert isinstance(result.assistant_text, str)
    assert result.tool_background_started == (
        bundle.expected_mode == UserTurnLlmLoopMode.DUAL_LLM.value
    )
