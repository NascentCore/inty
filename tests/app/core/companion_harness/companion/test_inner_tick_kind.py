"""Registry consistency: every inner-tick track binds to one ``InnerTickKindSpec`` row."""

from __future__ import annotations

from app.core.companion_harness.companion.inner_tick_kind import (
    INNER_TICK_KINDS,
    InnerTickKind,
    inner_tick_kind_for_track,
    inner_tick_spec,
)
from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    InnerTickActivity,
    InnerTickThrottleKind,
    MONOLOG_INNER_TICK_CHAT_HISTORY_USER_MARKER,
)
from app.core.companion_harness.prompting.system_messages import (
    build_system_messages_for_inner_tick_autonomy,
    build_system_messages_for_inner_tick_monolog,
)
from app.core.companion_harness.companion.proactive_chat import (
    PROACTIVE_CHAT_TRANSCRIPT_USER_MARKER,
)

_INNER_TICK_TRACKS = (
    CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT,
    CompanionTurnTrack.INNER_TICK_SCHEDULED,
    CompanionTurnTrack.INNER_TICK_MONOLOG,
    CompanionTurnTrack.INNER_TICK_AUTONOMY,
)


def test_every_inner_tick_track_has_registry_kind() -> None:
    for track in _INNER_TICK_TRACKS:
        assert inner_tick_kind_for_track(track) is not None


def test_registry_covers_design_four_kinds() -> None:
    assert set(INNER_TICK_KINDS) == {
        InnerTickKind.MONOLOG,
        InnerTickKind.AUTONOMY,
        InnerTickKind.PROACTIVE_CHAT,
        InnerTickKind.SCHEDULED,
    }


def test_monolog_spec_matches_hardcoded_binding() -> None:
    spec = inner_tick_spec(InnerTickKind.MONOLOG)
    assert spec.activity == InnerTickActivity.MONOLOG
    assert spec.turn_track == CompanionTurnTrack.INNER_TICK_MONOLOG
    assert spec.throttle_kind == InnerTickThrottleKind.MONOLOG
    assert (
        spec.chat_history_marker
        == MONOLOG_INNER_TICK_CHAT_HISTORY_USER_MARKER
    )
    assert spec.suppresses_user_delivery is False
    assert (
        spec.async_tool_prompt_builder
        is build_system_messages_for_inner_tick_monolog
    )


def test_autonomy_spec_matches_hardcoded_binding() -> None:
    spec = inner_tick_spec(InnerTickKind.AUTONOMY)
    assert spec.activity == InnerTickActivity.AUTONOMY
    assert spec.turn_track == CompanionTurnTrack.INNER_TICK_AUTONOMY
    assert spec.throttle_kind == InnerTickThrottleKind.AUTONOMY
    assert spec.chat_history_marker == ""
    assert spec.suppresses_user_delivery is True
    assert (
        spec.async_tool_prompt_builder
        is build_system_messages_for_inner_tick_autonomy
    )


def test_proactive_and_scheduled_have_no_async_tool_builder() -> None:
    proactive = inner_tick_spec(InnerTickKind.PROACTIVE_CHAT)
    scheduled = inner_tick_spec(InnerTickKind.SCHEDULED)
    assert proactive.async_tool_prompt_builder is None
    assert scheduled.async_tool_prompt_builder is None
    assert (
        proactive.chat_history_marker
        == PROACTIVE_CHAT_TRANSCRIPT_USER_MARKER
    )
    assert scheduled.chat_history_marker == ""
