"""Resolve companion turn tracks to AgenticLoop turn plugins (#3401 slice 3b)."""

from __future__ import annotations

import pytest

from app.core.companion_harness.companion.models import CompanionTurnTrack
from app.core.companion_harness.loop.track_loop_plugin import (
    BootstrapUserChatPlugin,
    ImplicitSignOnGreetingPlugin,
    InnerTickChatOnlyPlugin,
    InnerTickToolLoopPlugin,
    SettledUserChatPlugin,
    resolve_agentic_loop,
)


@pytest.mark.parametrize(
    "track, expected_type",
    [
        (
            CompanionTurnTrack.USER_CHAT_BOOTSTRAP,
            BootstrapUserChatPlugin,
        ),
        (CompanionTurnTrack.USER_CHAT, SettledUserChatPlugin),
        (
            CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING,
            ImplicitSignOnGreetingPlugin,
        ),
        (
            CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT,
            InnerTickChatOnlyPlugin,
        ),
        (
            CompanionTurnTrack.INNER_TICK_SCHEDULED,
            InnerTickChatOnlyPlugin,
        ),
        (
            CompanionTurnTrack.INNER_TICK_MONOLOG,
            InnerTickToolLoopPlugin,
        ),
        (
            CompanionTurnTrack.INNER_TICK_AUTONOMY,
            InnerTickToolLoopPlugin,
        ),
    ],
)
def test_resolve_agentic_loop_returns_expected_plugin_type(
    track: CompanionTurnTrack,
    expected_type: type,
) -> None:
    plugin = resolve_agentic_loop(track=track)
    assert isinstance(plugin, expected_type)
