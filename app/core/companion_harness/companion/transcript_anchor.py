"""Shared real-user anchor helpers for proactive scheduling and ai_private splice."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .models import ChatMessage


@dataclass(frozen=True)
class RealUserTranscriptAnchor:
    """Last non-proactive user row in a transcript window."""

    ts: datetime | None
    uuid: str | None


def parse_transcript_row_ts(ts: str) -> datetime:
    s = ts.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


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
