"""Turn-track adapters for the companion kernel.

Production entrypoints choose a ``CompanionTurnTrack`` before calling the core
turn runner.  This module maps tracks to legacy kernel booleans
(``inner_tick_turn`` and ``InnerTickActivity``) and to LangSmith lane labels
used for trace filtering.


TODO(companion-package-reorg): Move this module into a focused sub-package under companion_harness (see issue body for draft layout). — #3409
https://github.com/NascentCore/inty/issues/3409"""

from __future__ import annotations

from .models import CompanionTurnTrack, InnerTickActivity


def turn_flags_for_track(
    track: CompanionTurnTrack,
) -> tuple[bool, InnerTickActivity]:
    """Translate a production track into the legacy kernel routing flags."""

    match track:
        case (
            CompanionTurnTrack.USER_CHAT
            | CompanionTurnTrack.USER_CHAT_BOOTSTRAP
            | CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING
        ):
            return False, InnerTickActivity.MAINTENANCE
        case CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT:
            return True, InnerTickActivity.PROACTIVE_CHAT
        case CompanionTurnTrack.INNER_TICK_SCHEDULED:
            return True, InnerTickActivity.PROACTIVE_CHAT
        case CompanionTurnTrack.INNER_TICK_MAINTENANCE:
            return True, InnerTickActivity.MAINTENANCE
        case CompanionTurnTrack.INNER_TICK_AUTONOMY:
            return True, InnerTickActivity.AUTONOMY


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
            | CompanionTurnTrack.INNER_TICK_MAINTENANCE
            | CompanionTurnTrack.INNER_TICK_AUTONOMY
        ):
            return "inner_tick"
