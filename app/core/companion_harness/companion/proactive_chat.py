"""Proactive chat scheduling and prompt copy for user-idle companion turns.

- **Scheduling**: ``next_proactive_chat_wait_seconds`` estimates rhythm from transcript gaps
  and config (base idle, min gap between proactive chat rounds, min transcript lines).
- **Copy**: system/user placeholders for ``InnerTickActivity.PROACTIVE_CHAT`` turns; main user
  marker path is ``build_proactive_chat_transcript_user_marker`` in the turn pipeline.
- **Transcript**: proactive rounds mark the synthetic user row with ``proactive_chat: true``
  so schedulers can anchor ``min_gap_sec`` separately from real user messages.
"""

from __future__ import annotations

import statistics
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field

from app.core.companion_harness.memory.memory_store import MemoryStore
from .models import ChatMessage, load_transcript_from_store

PROACTIVE_CHAT_SYNTHETIC_SYSTEM_MESSAGE = (
    "## Proactive Messaging\n"
    "- The user has not sent a new message for some time.\n"
    "- Based on the conversation context, your character's personality, and the time elapsed, decide whether to proactively send a message.\n"
    "- If you have something meaningful, respond appropriately.\n"
    "- If there is nothing appropriate to say right now, respond with exactly: [SILENT]\n"
)

PROACTIVE_CHAT_TRANSCRIPT_USER_MARKER = (
    "[SYSTEM PROACTIVE CHAT] The user has not sent a new message for some time."
)

_NEVER = 86400.0 * 365.0
_RHYTHM_CLAMP_SEC = (90.0, 900.0)


class ProactiveChatConfig(BaseModel):
    """Tuning for when companion may speak on ``PROACTIVE_CHAT`` inner ticks."""

    enabled: bool = Field(
        default=True,
        description=(
            "Master switch. When false, companion will not proactively chat while the user is idle."
        ),
    )
    base_idle_sec: float = Field(
        default=30.0,
        description=(
            "Base quiet period after the assistant's last **non-proactive-chat** reply before "
            "another proactive chat round may fire."
        ),
    )
    min_gap_sec: float = Field(
        default=60.0,
        description=(
            "Minimum interval anchored on the **last proactive-chat synthetic user** row; "
            "prevents back-to-back proactive chat while the user stays silent."
        ),
    )
    min_transcript_lines: int = Field(
        default=0,
        description=(
            "Minimum transcript lines before proactive chat scheduling is considered."
        ),
    )


def _parse_ts(ts: str) -> datetime:
    s = ts.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _user_message_gaps_seconds(msgs: list[ChatMessage]) -> list[float]:
    user_ts: list[datetime] = []
    for m in msgs:
        if m.role != "user":
            continue
        user_ts.append(_parse_ts(m.ts))
    if len(user_ts) < 2:
        return []
    gaps: list[float] = []
    for i in range(1, len(user_ts)):
        delta = (user_ts[i] - user_ts[i - 1]).total_seconds()
        if delta > 0:
            gaps.append(delta)
    return gaps[-5:]


def _rhythm_idle_seconds(msgs: list[ChatMessage], base: float) -> float:
    gaps = _user_message_gaps_seconds(msgs)
    if len(gaps) < 2:
        return base
    med = float(statistics.median(gaps))
    scaled = med * 0.65 + 20.0
    lo, hi = _RHYTHM_CLAMP_SEC
    return max(lo, min(hi, min(base * 2.0, scaled)))


def _last_assistant_ts(msgs: list[ChatMessage]) -> datetime | None:
    for m in reversed(msgs):
        if m.role == "assistant":
            return _parse_ts(m.ts)
    return None


def _format_elapsed_since(seconds: float) -> str:
    s = max(0, int(round(seconds)))
    if s < 60:
        return f"{s}s"
    if s < 3600:
        m, sec = divmod(s, 60)
        return f"{m}m {sec}s" if sec else f"{m}m"
    h, rem = divmod(s, 3600)
    m = rem // 60
    return f"{h}h {m}m" if m else f"{h}h"


def _is_proactive_chat_user_row(m: ChatMessage) -> bool:
    return m.proactive_chat is True


def _last_real_user_ts(msgs: list[ChatMessage]) -> datetime | None:
    for m in reversed(msgs):
        if m.role == "user" and not _is_proactive_chat_user_row(m):
            return _parse_ts(m.ts)
    return None


def build_proactive_chat_transcript_user_marker(
    msgs: list[ChatMessage],
    *,
    now: datetime | None = None,
) -> str:
    """English one-liner for proactive-chat tail user placeholder and transcript."""
    t = now if now is not None else datetime.now(timezone.utc)
    last_u = _last_real_user_ts(msgs)
    last_a = _last_assistant_ts(msgs)
    if last_u is None:
        u_seg = (
            "Time since the user's last message: no prior real user message in transcript."
        )
    else:
        u_seg = f"Time since the user's last message: {_format_elapsed_since((t - last_u).total_seconds())}."
    if last_a is None:
        a_seg = "Time since the assistant's last message: no prior assistant message in transcript."
    else:
        a_seg = f"Time since the assistant's last message: {_format_elapsed_since((t - last_a).total_seconds())}."
    return f"[SYSTEM PROACTIVE CHAT] {u_seg} {a_seg}"


def _last_proactive_chat_user_ts(msgs: list[ChatMessage]) -> datetime | None:
    for m in reversed(msgs):
        if m.role == "user" and _is_proactive_chat_user_row(m):
            return _parse_ts(m.ts)
    return None


def next_proactive_chat_wait_seconds(
    store: MemoryStore,
    config: ProactiveChatConfig,
    *,
    now: datetime | None = None,
) -> float:
    """Seconds until proactive chat may fire; <= 0 when due; large value when gated off."""
    if not config.enabled:
        return _NEVER

    msgs = load_transcript_from_store(store, "transcript.jsonl")
    if len(msgs) < config.min_transcript_lines:
        return _NEVER

    if not msgs or msgs[-1].role != "assistant":
        return _NEVER

    last_asst = _last_assistant_ts(msgs)
    if last_asst is None:
        return _NEVER

    t = now if now is not None else datetime.now(timezone.utc)
    rhythm = _rhythm_idle_seconds(msgs, config.base_idle_sec)
    earliest = last_asst + timedelta(seconds=rhythm)

    last_pc = _last_proactive_chat_user_ts(msgs)
    if last_pc is not None:
        pc_earliest = last_pc + timedelta(seconds=config.min_gap_sec)
        if pc_earliest > earliest:
            earliest = pc_earliest

    return (earliest - t).total_seconds()
