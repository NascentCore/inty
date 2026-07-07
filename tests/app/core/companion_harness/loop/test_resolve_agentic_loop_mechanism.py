from __future__ import annotations

import pytest

from app.core.companion_harness.companion.models import CompanionTurnTrack
from app.core.companion_harness.loop.config import (
    AgenticLoopMechanism,
    UserTurnLlmLoopMode,
    resolve_agentic_loop_mechanism,
)


@pytest.mark.parametrize(
    "track",
    [
        CompanionTurnTrack.USER_CHAT_BOOTSTRAP,
        CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING,
        CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT,
        CompanionTurnTrack.INNER_TICK_SCHEDULED,
        CompanionTurnTrack.INNER_TICK_MONOLOG,
        CompanionTurnTrack.INNER_TICK_AUTONOMY,
    ],
)
def test_non_user_chat_tracks_resolve_single_llm(
    track: CompanionTurnTrack,
) -> None:
    assert resolve_agentic_loop_mechanism(track=track) == (
        AgenticLoopMechanism.SINGLE_LLM
    )


def test_user_chat_resolves_single_llm_from_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.core.companion_harness.loop.config.resolved_user_turn_llm_loop_mode",
        lambda: UserTurnLlmLoopMode.IN_TURN_SINGLE_LLM,
    )
    assert (
        resolve_agentic_loop_mechanism(track=CompanionTurnTrack.USER_CHAT)
        == AgenticLoopMechanism.SINGLE_LLM
    )


def test_user_chat_resolves_dual_llm_from_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.core.companion_harness.loop.config.resolved_user_turn_llm_loop_mode",
        lambda: UserTurnLlmLoopMode.DUAL_LLM,
    )
    assert (
        resolve_agentic_loop_mechanism(track=CompanionTurnTrack.USER_CHAT)
        == AgenticLoopMechanism.DUAL_LLM
    )
