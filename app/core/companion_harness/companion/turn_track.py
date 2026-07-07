"""Turn-track helpers for LangSmith lanes and loop-stage transcript semantics."""

from __future__ import annotations

from .models import CompanionTurnTrack

_COMPANION_TURN_TRACKS_WITH_IN_LOOP_TRANSCRIPT_SYNC: frozenset[
    CompanionTurnTrack
] = frozenset(
    {
        CompanionTurnTrack.USER_CHAT,
        CompanionTurnTrack.USER_CHAT_BOOTSTRAP,
        CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT,
        CompanionTurnTrack.INNER_TICK_SCHEDULED,
        CompanionTurnTrack.INNER_TICK_MONOLOG,
        CompanionTurnTrack.INNER_TICK_AUTONOMY,
    }
)

_PROACTIVE_EMPTY_ASSISTANT_SKIP_TRACKS: frozenset[CompanionTurnTrack] = (
    frozenset(
        {
            CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT,
            CompanionTurnTrack.INNER_TICK_SCHEDULED,
        }
    )
)


def companion_turn_track_syncs_transcript_in_agentic_loop(
    track: CompanionTurnTrack,
) -> bool:
    """True when AgenticLoop persists user/assistant rows before turn.py post-loop."""
    return track in _COMPANION_TURN_TRACKS_WITH_IN_LOOP_TRANSCRIPT_SYNC


def companion_turn_track_skips_empty_proactive_assistant_row(
    track: CompanionTurnTrack,
) -> bool:
    """True when proactive envelope silence must not append an empty assistant row."""
    return track in _PROACTIVE_EMPTY_ASSISTANT_SKIP_TRACKS


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
