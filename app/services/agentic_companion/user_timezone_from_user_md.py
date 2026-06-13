"""Infer user IANA timezone from persisted USER.md for agent-channel turns."""

from __future__ import annotations

import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from loguru import logger

_IANA_PATTERN = re.compile(r"\b([A-Za-z][A-Za-z0-9_+-]*/[A-Za-z][A-Za-z0-9_+-]*)\b")
_TIMEZONE_LABEL_MARKERS = (
    "时区",
    "timezone",
    "time zone",
)
_IDENTITY_SECTION = "## 身份信息"


def _valid_iana_timezone(name: str) -> str | None:
    try:
        return ZoneInfo(name).key
    except ZoneInfoNotFoundError:
        return None


def _line_mentions_timezone_label(line: str) -> bool:
    lowered = line.casefold()
    return any(marker.casefold() in lowered for marker in _TIMEZONE_LABEL_MARKERS)


def _first_iana_in_line(line: str) -> str | None:
    for match in _IANA_PATTERN.finditer(line):
        validated = _valid_iana_timezone(match.group(1))
        if validated is not None:
            return validated
    return None


def _identity_section_lines(user_md: str) -> list[str]:
    lines = user_md.splitlines()
    if _IDENTITY_SECTION not in lines:
        return lines
    start = lines.index(_IDENTITY_SECTION) + 1
    out: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        out.append(line)
    return out


def infer_iana_timezone_from_user_md(user_md: str) -> str | None:
    """Return IANA timezone when USER.md records one under identity facts."""
    if not user_md.strip():
        return None
    identity_lines = _identity_section_lines(user_md)
    for line in identity_lines:
        if not _line_mentions_timezone_label(line):
            continue
        tz = _first_iana_in_line(line)
        if tz is not None:
            return tz
    for line in identity_lines:
        tz = _first_iana_in_line(line)
        if tz is not None:
            logger.debug(
                "user_timezone_inference iana_in_identity_without_label tz={}",
                tz,
            )
            return tz
    return None
