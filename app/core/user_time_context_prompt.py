"""Shared markdown for ##User Time Context (classic Agent + companion implicit signals)."""

from __future__ import annotations

from typing import Any, Mapping

MINUTES_PER_HOUR = 60

USER_TIME_CONTEXT_SYSTEM_PROMPT_TITLE = "##User Time Context"
USER_TIME_CONTEXT_SYSTEM_PROMPT_GUIDANCE = [
    "- This time reflects the user's local time, not the assistant's.",
    "- Use it only as context for the user's situation and daily rhythm.",
    "- You may softly infer typical human activities from the local hour (for example "
    "morning routines or breakfast, midday work or lunch, evening wind-down or dinner, "
    "late night rest) as loose priors, not facts about this user.",
    "- Treat these as gentle scene context; avoid lecturing or assuming their schedule.",
    "- Do not claim to need sleep or be offline.",
]


def format_utc_offset_minutes(offset_minutes: int) -> str:
    sign = "+" if offset_minutes >= 0 else "-"
    total_minutes = abs(offset_minutes)
    hours, minutes = divmod(total_minutes, MINUTES_PER_HOUR)
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def build_user_time_context_markdown(
    user_time_context: Mapping[str, Any] | None,
) -> str | None:
    """Same contract as legacy ``Agent._build_user_time_context_prompt`` (TypedDict-shaped mapping)."""
    if not user_time_context:
        return None

    lines = [USER_TIME_CONTEXT_SYSTEM_PROMPT_TITLE]

    local_time = user_time_context.get("local_time")
    if local_time:
        lines.append(f"- User local time: {local_time}")

    tz = user_time_context.get("timezone")
    if tz:
        lines.append(f"- User timezone: {tz}")

    utc_offset_minutes = user_time_context.get("utc_offset_minutes")
    if isinstance(utc_offset_minutes, int):
        lines.append(f"- UTC offset: {format_utc_offset_minutes(utc_offset_minutes)}")

    if len(lines) == 1:
        return None

    lines.extend(USER_TIME_CONTEXT_SYSTEM_PROMPT_GUIDANCE)
    return "\n".join(lines)
