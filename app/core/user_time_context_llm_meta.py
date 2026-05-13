"""LLM-facing lines derived from ``UserTimeContext`` payloads.

Used by companion ``## user-time-context`` system slices and by classic agent
tail-user suffixes so both paths share one contract.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

_LINE_USER_TIME = "User's time: "
_LINE_TIME_ZONE = "Time zone: "


def _format_local_time_wall_minutes(local_time: str) -> str | None:
    raw = local_time.strip()
    if not raw:
        return None
    normalized = raw.replace("Z", "+00:00", 1) if raw.endswith("Z") else raw
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    dt = dt.replace(second=0, microsecond=0)
    return dt.strftime("%Y/%m/%d %H:%M")


def build_user_time_context_meta_lines(
    user_time_context: Mapping[str, Any] | None,
) -> list[str]:
    """Build zero to two factual lines for LLM prompts (no UTC offset line)."""
    if not user_time_context:
        return []
    meta_lines: list[str] = []
    local_time = user_time_context.get("local_time")
    if isinstance(local_time, str):
        wall = _format_local_time_wall_minutes(local_time)
        if wall is not None:
            meta_lines.append(f"{_LINE_USER_TIME}{wall}")

    tz = user_time_context.get("timezone")
    if isinstance(tz, str) and tz.strip():
        meta_lines.append(f"{_LINE_TIME_ZONE}{tz.strip()}")

    return meta_lines
