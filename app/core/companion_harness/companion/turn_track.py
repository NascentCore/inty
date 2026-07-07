"""Turn-track adapters for the companion kernel.

``turn_flags_for_track`` is a LangSmith-only legacy bridge (see ``llm_chat_runtime``).
``langsmith_inty_turn_lane_for_companion_track`` groups traces by coarse lane.

TODO(#3401): remove ``turn_flags_for_track`` once LangSmith metadata is track-native.
"""

from __future__ import annotations

from .models import CompanionTurnTrack, InnerTickActivity
from .inner_tick_kind import inner_tick_kind_for_track, inner_tick_spec


def turn_flags_for_track(
    track: CompanionTurnTrack,
) -> tuple[bool, InnerTickActivity]:
    """Translate a production track into legacy LangSmith routing flags."""

    kind = inner_tick_kind_for_track(track)
    if kind is not None:
        return True, inner_tick_spec(kind).activity
    return False, InnerTickActivity.MONOLOG


def langsmith_inty_turn_lane_for_companion_track(
    track: CompanionTurnTrack,
) -> str:
    """Return the coarse LangSmith lane name for trace grouping."""

    match track:
        case (
            CompanionTurnTrack.USER_CHAT
            | CompanionTurnTrack.USER_CHAT_BOOTSTRAP
        ):
            return "explicit_user_message"
        case CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING:
            return "implicit_turn"
        case (
            CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT
            | CompanionTurnTrack.INNER_TICK_SCHEDULED
            | CompanionTurnTrack.INNER_TICK_MONOLOG
            | CompanionTurnTrack.INNER_TICK_AUTONOMY
        ):
            return "inner_tick"
