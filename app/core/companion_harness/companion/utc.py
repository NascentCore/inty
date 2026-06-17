"""Timestamps: UTC for transcript; local TZ for diary lines and calendar-day paths.

TODO(companion-package-reorg): Move this module into a focused sub-package under companion_harness (see issue body for draft layout).
https://github.com/NascentCore/inty/issues/3409"""

from __future__ import annotations

import re
from datetime import datetime, timezone

_LLM_TS_SUFFIX_UTC = " UTC"
_TRANSCRIPT_TIMESTAMP_PREFIX_RE = re.compile(
    r"^(?:\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC\] )+"
)


def utc_now() -> datetime:
    """Current UTC wall time with second precision."""
    return datetime.now(timezone.utc).replace(microsecond=0)


def utc_iso_ts() -> str:
    """UTC ISO8601 with second precision for transcript persistence."""
    return utc_now().isoformat()


def utc_date_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def local_iso_ts() -> str:
    return datetime.now().astimezone().isoformat()


def local_date_str() -> str:
    return datetime.now().astimezone().date().isoformat()


def parse_utc_iso_ts(ts: str, *, allow_naive: bool) -> datetime:
    """Parse ISO timestamps into UTC; transcript callers may accept legacy naive rows."""
    assert ts
    normalized = ts.replace("Z", "+00:00") if ts.endswith("Z") else ts
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        if not allow_naive:
            raise ValueError("timestamp must include timezone offset or Z")
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def format_transcript_ts_for_llm_dt(dt: datetime) -> str:
    """Human-readable UTC label from a timezone-aware or naive datetime."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt_utc = dt.astimezone(timezone.utc).replace(microsecond=0)
    return dt_utc.strftime("%Y-%m-%d %H:%M:%S") + _LLM_TS_SUFFIX_UTC


def format_transcript_ts_for_llm(ts: str) -> str | None:
    """Human-readable UTC label for LLM message prefixes, or ``None`` if unparseable."""
    raw = ts
    if not raw:
        return None
    try:
        dt = parse_utc_iso_ts(raw, allow_naive=True)
    except ValueError:
        return None
    return format_transcript_ts_for_llm_dt(dt)


def strip_leading_transcript_timestamp_prefixes(content: str) -> str:
    """Remove harness LLM-only ``[YYYY-MM-DD HH:MM:SS UTC]`` prefixes from visible text."""
    return _TRANSCRIPT_TIMESTAMP_PREFIX_RE.sub("", content)


def transcript_message_content_for_llm(*, content: str, ts: str) -> str:
    """Prefix transcript ``content`` for LLM prompts only; stored rows stay bare."""
    bare = strip_leading_transcript_timestamp_prefixes(content)
    label = format_transcript_ts_for_llm(ts)
    if label is None:
        return bare
    return f"[{label}] {bare}"


def transcript_message_content_for_llm_at(*, content: str, at: datetime) -> str:
    """Prefix ``content`` with ``at`` for the tail user message in one LLM turn."""
    bare = strip_leading_transcript_timestamp_prefixes(content)
    label = format_transcript_ts_for_llm_dt(at)
    return f"[{label}] {bare}"
