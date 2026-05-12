"""User local time context for LLM requests.

Classic Agent and the companion kernel append a short factual tail to the **last user**
message (see ``suffix_user_text_with_time_context_lines``) when
``experimental_enable_chat_with_user_time_context`` is enabled, instead of injecting a
long system block. ``format_utc_offset_minutes`` formats ``utc_offset_minutes`` for the
optional ``user-time-utc-offset:`` line.
"""

from __future__ import annotations

from typing import Any, Mapping

MINUTES_PER_HOUR = 60


def format_utc_offset_minutes(offset_minutes: int) -> str:
    sign = "+" if offset_minutes >= 0 else "-"
    total_minutes = abs(offset_minutes)
    hours, minutes = divmod(total_minutes, MINUTES_PER_HOUR)
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def suffix_user_text_with_time_context_lines(
    user_text: str,
    user_time_context: Mapping[str, Any] | None,
    *,
    enabled: bool,
) -> str:
    """Append ``user-time:`` / ``user-time-zone:`` / optional ``user-time-utc-offset:`` after ``user_text``.

    When ``enabled`` is false, or ``user_time_context`` is empty, or no field yields a
    non-empty line, returns ``user_text`` unchanged. Lines with missing or blank values
    are omitted entirely (no empty key lines). A blank line separates the body from the
    suffix block; suffix lines use single ``\\n`` between them.
    """
    if not enabled or not user_time_context:
        return user_text

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
            f"user-time-utc-offset: {format_utc_offset_minutes(utc_offset_minutes)}"
        )

    if not meta_lines:
        return user_text

    return f"{user_text}\n\n" + "\n".join(meta_lines)
