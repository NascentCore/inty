"""Pure translation between CompanionTurnTrack and legacy kernel flags / LangSmith lanes."""

from __future__ import annotations

import pytest

from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    InnerTickActivity,
    inner_tick_activity_suppresses_user_delivery,
)
from app.core.companion_harness.companion.turn_track import (
    langsmith_inty_turn_lane_for_companion_track,
    turn_flags_for_track,
)


@pytest.mark.parametrize(
    "track, expect_inner, expect_activity",
    [
        (CompanionTurnTrack.USER_CHAT, False, InnerTickActivity.MONOLOG),
        (
            CompanionTurnTrack.USER_CHAT_BOOTSTRAP,
            False,
            InnerTickActivity.MONOLOG,
        ),
        (
            CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING,
            False,
            InnerTickActivity.MONOLOG,
        ),
        (
            CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT,
            True,
            InnerTickActivity.PROACTIVE_CHAT,
        ),
        (
            CompanionTurnTrack.INNER_TICK_SCHEDULED,
            True,
            InnerTickActivity.PROACTIVE_CHAT,
        ),
        (
            CompanionTurnTrack.INNER_TICK_MONOLOG,
            True,
            InnerTickActivity.MONOLOG,
        ),
        (
            CompanionTurnTrack.INNER_TICK_AUTONOMY,
            True,
            InnerTickActivity.AUTONOMY,
        ),
    ],
)
def test_turn_flags_for_track(
    track: CompanionTurnTrack,
    expect_inner: bool,
    expect_activity: InnerTickActivity,
) -> None:
    inner, activity = turn_flags_for_track(track)
    assert inner is expect_inner
    assert activity == expect_activity


def test_autonomy_suppresses_user_delivery() -> None:
    assert inner_tick_activity_suppresses_user_delivery(
        InnerTickActivity.AUTONOMY
    )
    assert not inner_tick_activity_suppresses_user_delivery(
        InnerTickActivity.MONOLOG
    )


def test_autonomy_langsmith_lane_groups_with_inner_tick() -> None:
    assert (
        langsmith_inty_turn_lane_for_companion_track(
            CompanionTurnTrack.INNER_TICK_AUTONOMY
        )
        == "inner_tick"
    )
