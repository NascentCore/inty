"""Companion-local user wall-clock facts for one LLM turn.

Duplicate of the factual line rules in ``app.core.user_time_context_prompt`` so the
harness can inject a dedicated ``## user-time-context`` **system** slice before the
tail **user** message without importing or changing that legacy-oriented module.

Intention: keep companion prompt assembly self-contained; classic Agent continues to
suffix the last user string via ``suffix_user_text_with_time_context_lines``.
"""

from __future__ import annotations

from typing import Any, Mapping

MINUTES_PER_HOUR = 60

USER_TIME_CONTEXT_SYSTEM_HEADER = "## user-time-context"


def _format_utc_offset_minutes(offset_minutes: int) -> str:
    sign = "+" if offset_minutes >= 0 else "-"
    total_minutes = abs(offset_minutes)
    hours, minutes = divmod(total_minutes, MINUTES_PER_HOUR)
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def _meta_lines_from_user_time_context(
    user_time_context: Mapping[str, Any],
) -> list[str]:
    meta_lines: list[str] = []
    local_time = user_time_context.get("local_time")
    if isinstance(local_time, str) and local_time.strip():
        meta_lines.append(f"user-time: {local_time.strip()}")

    tz = user_time_context.get("timezone")
    if isinstance(tz, str) and tz.strip():
        meta_lines.append(f"user-time-zone: {tz.strip()}")

    utc_offset_minutes = user_time_context.get("utc_offset_minutes")
    if isinstance(utc_offset_minutes, int):
        meta_lines.append(
            f"user-time-utc-offset: {_format_utc_offset_minutes(utc_offset_minutes)}"
        )
    return meta_lines


def build_companion_user_time_context_system_content(
    user_time_context: Mapping[str, Any] | None,
    *,
    enabled: bool,
) -> str | None:
    """Return one system message body, or ``None`` when nothing should be injected.

    First line is ``USER_TIME_CONTEXT_SYSTEM_HEADER``; following lines match the
    companion-era ``user-time:`` / ``user-time-zone:`` / ``user-time-utc-offset:``
    contract (blank fields omitted).
    """
    if not enabled or not user_time_context:
        return None
    meta_lines = _meta_lines_from_user_time_context(user_time_context)
    if not meta_lines:
        return None
    return USER_TIME_CONTEXT_SYSTEM_HEADER + "\n" + "\n".join(meta_lines)
