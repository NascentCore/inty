"""Timestamps: UTC for transcript; local TZ for diary lines and calendar-day paths."""

from __future__ import annotations

from datetime import datetime, timezone

_LLM_TS_SUFFIX_UTC = " UTC"


def utc_iso_ts() -> str:
    """UTC ISO8601 with second precision for transcript persistence."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def utc_date_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def local_iso_ts() -> str:
    return datetime.now().astimezone().isoformat()


def local_date_str() -> str:
    return datetime.now().astimezone().date().isoformat()


def format_transcript_ts_for_llm(ts: str) -> str | None:
    """Human-readable UTC label for LLM message prefixes, or ``None`` if unparseable."""
    raw = ts
    if not raw:
        return None
    normalized = raw.replace("Z", "+00:00") if raw.endswith("Z") else raw
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt_utc = dt.astimezone(timezone.utc).replace(microsecond=0)
    return dt_utc.strftime("%Y-%m-%d %H:%M:%S") + _LLM_TS_SUFFIX_UTC


def transcript_message_content_for_llm(*, content: str, ts: str) -> str:
    """Prefix transcript ``content`` for LLM prompts only; stored rows stay bare."""
    label = format_transcript_ts_for_llm(ts)
    if label is None:
        return content
    return f"[{label}] {content}"
