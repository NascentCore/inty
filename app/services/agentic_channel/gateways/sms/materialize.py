"""SMS body materialization for gateway downlink delivery.

Generated entirely by Cursor agent.
"""

from __future__ import annotations

import re

_SMS_SEGMENT_LENGTH = 160
_MARKDOWN_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\*\*(.+?)\*\*"), r"\1"),
    (re.compile(r"__(.+?)__"), r"\1"),
    (re.compile(r"\*(.+?)\*"), r"\1"),
    (re.compile(r"_(.+?)_"), r"\1"),
    (re.compile(r"`(.+?)`"), r"\1"),
    (re.compile(r"^#{1,6}\s+", re.MULTILINE), ""),
    (re.compile(r"^\s*[-*]\s+", re.MULTILINE), ""),
)


def _strip_markdown(text: str) -> str:
    cleaned = text
    for pattern, replacement in _MARKDOWN_PATTERNS:
        cleaned = pattern.sub(replacement, cleaned)
    return cleaned


def materialize_sms_body(text: str) -> tuple[str, ...]:
    """Normalize assistant text into one or more GSM-friendly SMS segments."""
    assert text is not None
    collapsed = " ".join(_strip_markdown(text).split())
    if not collapsed:
        return ()
    segments: list[str] = []
    start = 0
    while start < len(collapsed):
        segments.append(collapsed[start : start + _SMS_SEGMENT_LENGTH])
        start += _SMS_SEGMENT_LENGTH
    return tuple(segments)
