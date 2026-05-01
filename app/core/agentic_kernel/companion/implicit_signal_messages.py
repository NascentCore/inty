"""OpenAI-style system slices from ImplicitSignalBundle.

Keep USER_TIME_CONTEXT_* title and guidance lines in lockstep with
``app/core/agent/agent.py`` (``_build_user_time_context_prompt``).
"""

from __future__ import annotations

from typing import Any

from app.schemas.chat import UserTimeContext
from app.schemas.implicit_signals import ImplicitSignalBundle

MINUTES_PER_HOUR = 60

# Sync with app.core.agent.agent: USER_TIME_CONTEXT_SYSTEM_PROMPT_TITLE / GUIDANCE
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


def _format_utc_offset_minutes(offset_minutes: int) -> str:
    sign = "+" if offset_minutes >= 0 else "-"
    total_minutes = abs(offset_minutes)
    hours, minutes = divmod(total_minutes, MINUTES_PER_HOUR)
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def _build_user_time_context_markdown(client_time: UserTimeContext | None) -> str | None:
    if client_time is None:
        return None
    lines = [USER_TIME_CONTEXT_SYSTEM_PROMPT_TITLE]
    if client_time.local_time:
        lines.append(f"- User local time: {client_time.local_time}")
    if client_time.timezone:
        lines.append(f"- User timezone: {client_time.timezone}")
    if isinstance(client_time.utc_offset_minutes, int):
        lines.append(
            f"- UTC offset: {_format_utc_offset_minutes(client_time.utc_offset_minutes)}"
        )
    if len(lines) == 1:
        return None
    lines.extend(USER_TIME_CONTEXT_SYSTEM_PROMPT_GUIDANCE)
    return "\n".join(lines)


def implicit_signal_system_messages(
    bundle: ImplicitSignalBundle | None,
) -> list[dict[str, Any]]:
    """Return zero or one system message dicts for model-visible implicit signals."""
    if bundle is None:
        return []
    text = _build_user_time_context_markdown(bundle.client_time)
    if not text:
        return []
    return [{"role": "system", "content": text}]
