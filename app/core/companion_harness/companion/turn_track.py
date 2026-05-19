"""Map ``CompanionTurnTrack`` to kernel bools and LangSmith lane labels."""

from __future__ import annotations

from app.schemas.implicit_signals import ImplicitSignalBundle

from .implicit_signal_messages import implicit_user_signed_on_chat_turn
from .models import CompanionTurnTrack, InnerTickActivity


def turn_flags_for_track(
    track: CompanionTurnTrack,
) -> tuple[bool, InnerTickActivity]:
    match track:
        case (
            CompanionTurnTrack.USER_CHAT
            | CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING
        ):
            return False, InnerTickActivity.MAINTENANCE
        case CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT:
            return True, InnerTickActivity.PROACTIVE_CHAT
        case CompanionTurnTrack.INNER_TICK_SCHEDULED:
            return True, InnerTickActivity.PROACTIVE_CHAT
        case CompanionTurnTrack.INNER_TICK_MAINTENANCE:
            return True, InnerTickActivity.MAINTENANCE


def track_from_legacy_flags(
    *,
    inner_tick_turn: bool,
    inner_tick_activity: InnerTickActivity,
    implicit_signal_bundle: ImplicitSignalBundle | None,
) -> CompanionTurnTrack:
    if inner_tick_turn:
        match inner_tick_activity:
            case InnerTickActivity.PROACTIVE_CHAT:
                return CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT
            case InnerTickActivity.MAINTENANCE:
                return CompanionTurnTrack.INNER_TICK_MAINTENANCE
    if implicit_user_signed_on_chat_turn(
        implicit_signal_bundle=implicit_signal_bundle,
        inner_tick_turn=False,
    ):
        return CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING
    return CompanionTurnTrack.USER_CHAT


def langsmith_inty_turn_lane_for_companion_track(
    track: CompanionTurnTrack,
) -> str:
    match track:
        case CompanionTurnTrack.USER_CHAT:
            return "explicit_user_message"
        case CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING:
            return "implicit_turn"
        case (
            CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT
            | CompanionTurnTrack.INNER_TICK_SCHEDULED
            | CompanionTurnTrack.INNER_TICK_MAINTENANCE
        ):
            return "inner_tick"
