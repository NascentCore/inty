"""Turn-track adapters for the companion kernel.

Production entrypoints choose a ``CompanionTurnTrack`` before calling the core
turn runner.  This module maps tracks to legacy kernel booleans
(``inner_tick_turn`` and ``InnerTickActivity``) and to LangSmith lane labels
used for trace filtering.
"""

from __future__ import annotations

from .models import CompanionTurnTrack, InnerTickActivity
from .turn_routes import TurnRouteMode


def in_turn_sync_tool_loop_active(
    *,
    track: CompanionTurnTrack,
    route_mode: TurnRouteMode,
) -> bool:
    """Whether ``run_turn`` should use the in-turn sync tool loop for this track."""
    match track:
        case CompanionTurnTrack.USER_CHAT_BOOTSTRAP:
            return True
        case CompanionTurnTrack.USER_CHAT:
            return route_mode == TurnRouteMode.IN_TURN_SYNC_TOOL
        case _:
            return False


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
