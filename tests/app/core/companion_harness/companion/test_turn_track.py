"""Pure translation between CompanionTurnTrack and LangSmith lanes."""

from __future__ import annotations

import pytest

from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
)
from app.core.companion_harness.companion.turn_track import (
    companion_turn_track_syncs_transcript_in_agentic_loop,
    langsmith_inty_turn_lane_for_companion_track,
)


def test_autonomy_langsmith_lane_groups_with_inner_tick() -> None:
    assert (
        langsmith_inty_turn_lane_for_companion_track(
            CompanionTurnTrack.INNER_TICK_AUTONOMY
        )
        == "inner_tick"
    )


@pytest.mark.parametrize(
    "track, expected",
    [
        (CompanionTurnTrack.USER_CHAT, True),
        (CompanionTurnTrack.USER_CHAT_BOOTSTRAP, True),
        (CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT, True),
        (CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING, False),
    ],
)
def test_companion_turn_track_syncs_transcript_in_agentic_loop(
    track: CompanionTurnTrack,
    expected: bool,
) -> None:
    assert (
        companion_turn_track_syncs_transcript_in_agentic_loop(track) is expected
    )
