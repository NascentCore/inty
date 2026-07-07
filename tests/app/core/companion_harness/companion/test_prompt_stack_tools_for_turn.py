"""Track-derived OpenAI tool schema selection for companion turns."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from app.core.companion_harness.companion.models import CompanionTurnTrack
from app.core.companion_harness.companion.prompt_stack import (
    companion_tools_for_turn,
)
from app.core.companion_harness.tools.companion_tool_runtime import (
    build_openai_bootstrap_track_tools,
    build_openai_repl_tools,
    build_openai_repl_tools_inner_tick,
    build_openai_repl_tools_inner_tick_autonomy,
)


@pytest.mark.parametrize(
    "track, expected",
    [
        (CompanionTurnTrack.USER_CHAT, build_openai_repl_tools),
        (
            CompanionTurnTrack.USER_CHAT_BOOTSTRAP,
            build_openai_bootstrap_track_tools,
        ),
        (CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING, lambda: []),
        (CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT, lambda: []),
        (CompanionTurnTrack.INNER_TICK_SCHEDULED, lambda: []),
        (
            CompanionTurnTrack.INNER_TICK_MONOLOG,
            build_openai_repl_tools_inner_tick,
        ),
        (
            CompanionTurnTrack.INNER_TICK_AUTONOMY,
            build_openai_repl_tools_inner_tick_autonomy,
        ),
    ],
)
def test_companion_tools_for_turn_by_track(
    track: CompanionTurnTrack,
    expected: Callable[[], list[dict[str, Any]]],
) -> None:
    assert companion_tools_for_turn(track=track) == expected()


def test_user_chat_implicit_sign_on_clears_tools() -> None:
    assert (
        companion_tools_for_turn(
            track=CompanionTurnTrack.USER_CHAT,
            implicit_user_signed_on_turn=True,
        )
        == []
    )
