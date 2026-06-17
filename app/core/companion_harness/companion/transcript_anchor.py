"""Shared real-user anchor helpers for proactive scheduling and ai_private splice."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .models import ChatMessage
from .utc import parse_utc_iso_ts


@dataclass(frozen=True)
class RealUserTranscriptAnchor:
    """Last non-proactive user row in a transcript window."""

    ts: datetime | None
    uuid: str | None


def parse_transcript_row_ts(ts: str) -> datetime:
    """Parse transcript ``ts`` values as timezone-aware UTC datetimes."""
    return parse_utc_iso_ts(ts, allow_naive=True)


parse_transcript_datetime = parse_transcript_row_ts


def last_real_user_transcript_anchor(
    msgs: list[ChatMessage],
) -> RealUserTranscriptAnchor:
    for row in reversed(msgs):
        if row.role != "user" or row.proactive_chat is True:
            continue
        row_uuid = row.uuid
        uuid = row_uuid.strip() if isinstance(row_uuid, str) and row_uuid.strip() else None
        return RealUserTranscriptAnchor(ts=parse_transcript_row_ts(row.ts), uuid=uuid)
    return RealUserTranscriptAnchor(ts=None, uuid=None)
