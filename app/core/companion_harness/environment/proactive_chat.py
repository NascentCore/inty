"""Proactive chat scheduling and prompt copy for user-idle companion turns.

- **Scheduling**: ``next_proactive_chat_wait_seconds`` uses ``last_assistant_ts + rhythm``;
  ``rhythm = min(max(exponential, median), stop_after_silence)`` where exponential is
  ``N × 2^k`` (``k`` = proactive rounds since last real user) and median adapts from
  real-user gaps; total silence since last real user beyond ``stop_after_silence`` stops proactive.
- **Usage**: proactive turns are not gated by daily message count; future limits use token
  consumption (see companion WS proactive path NOTE in ``app.utils.config``).
- **Copy**: system/user placeholders for ``InnerTickActivity.PROACTIVE_CHAT`` turns.
- **Transcript**: proactive rounds mark the synthetic user row with ``proactive_chat: true``
  (for markers and LLM context; not used as a separate scheduling anchor).

Full WS worker / poll / maintenance relationship: ``docs/companion_harness/INNER_TICK_SCHEDULING.md``.
"""

from __future__ import annotations

import statistics
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field

from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.runtime.models import ChatMessage, load_transcript_from_store

PROACTIVE_CHAT_SYNTHETIC_SYSTEM_MESSAGE = (
    "## Proactive Messaging\n"
    "- The user has not sent a new message for some time.\n"
    "- Based on the conversation context, your character's personality, and the time elapsed, decide whether to proactively send a message.\n"
    '- You may **continue** the current thread when it still has momentum, **or initiate a new topic** when the prior beat landed, the scene feels closed, or enough time passed — e.g. a passing thought, playful question, something you "just noticed", a check-in grounded in USER/MEMORY, or a small daily moment.\n'
    "- New topics must feel in-character and relationally continuous; do not meta-reference proactive messaging or time gaps.\n"
    "- If you have something meaningful, respond appropriately.\n"
    "- If there is nothing appropriate to say right now, respond with exactly: [SILENT]\n"
)

PROACTIVE_CHAT_TRANSCRIPT_USER_MARKER = (
    "[SYSTEM PROACTIVE CHAT] The user has not sent a new message for some time."
)

PROACTIVE_CHAT_SILENT_TOKEN = "[SILENT]"

_NEVER = 86400.0 * 365.0


class ProactiveChatConfig(BaseModel):
    """Tuning for when companion may speak on ``PROACTIVE_CHAT`` inner ticks."""

    base_idle_sec: float = Field(
        default=30.0,
        description=(
            "Base quiet period after the assistant's last reply before another "
            "proactive chat round may fire; also the rhythm fallback when transcript "
            "has fewer than two real-user gaps."
        ),
    )
    min_transcript_lines: int = Field(
        default=0,
        description=(
            "Minimum transcript lines before proactive chat scheduling is considered."
        ),
    )
    stop_after_silence_minutes: float = Field(
        default=30.0,
        description=(
            "Cap each proactive wait interval and stop proactive "
            "when time since the last real user message exceeds this threshold."
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
        if m.proactive_chat is True:
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
    return min(base * 2.0, scaled)


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


def _last_real_user_ts(msgs: list[ChatMessage]) -> datetime | None:
    for m in reversed(msgs):
        if m.role == "user" and m.proactive_chat is not True:
            return _parse_ts(m.ts)
    return None


def _proactive_rounds_since_last_real_user(msgs: list[ChatMessage]) -> int:
    """Count synthetic proactive user rows after the last real user message."""
    count = 0
    for m in reversed(msgs):
        if m.role == "user" and m.proactive_chat is not True:
            break
        if m.role == "user" and m.proactive_chat is True:
            count += 1
    return count


def _combined_rhythm_seconds(
    msgs: list[ChatMessage],
    *,
    k: int,
    base: float,
    stop_sec: float,
) -> float:
    """``min(max(exponential, median), stop_sec)`` for the next proactive wait."""
    exponential = min(base * (2**k), stop_sec)
    median = _rhythm_idle_seconds(msgs, base)
    return min(max(exponential, median), stop_sec)


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
        u_seg = "Time since the user's last message: no prior real user message in transcript."
    else:
        u_seg = f"Time since the user's last message: {_format_elapsed_since((t - last_u).total_seconds())}."
    if last_a is None:
        a_seg = "Time since the assistant's last message: no prior assistant message in transcript."
    else:
        a_seg = f"Time since the assistant's last message: {_format_elapsed_since((t - last_a).total_seconds())}."
    return f"[SYSTEM PROACTIVE CHAT] {u_seg} {a_seg}"


def next_proactive_chat_wait_seconds(
    store: MemoryStore,
    config: ProactiveChatConfig,
    *,
    now: datetime | None = None,
) -> float:
    """Seconds until proactive chat may fire; <= 0 when due; large value when gated off."""
    msgs = load_transcript_from_store(store, "transcript.jsonl")
    if len(msgs) < config.min_transcript_lines:
        return _NEVER

    if not msgs or msgs[-1].role != "assistant":
        return _NEVER

    last_asst = _last_assistant_ts(msgs)
    if last_asst is None:
        return _NEVER

    t = now if now is not None else datetime.now(timezone.utc)
    stop_sec = config.stop_after_silence_minutes * 60.0
    last_real_user = _last_real_user_ts(msgs)
    if last_real_user is not None:
        silence_sec = (t - last_real_user).total_seconds()
        if silence_sec > stop_sec:
            return _NEVER

    k = _proactive_rounds_since_last_real_user(msgs)
    rhythm = _combined_rhythm_seconds(
        msgs,
        k=k,
        base=config.base_idle_sec,
        stop_sec=stop_sec,
    )
    earliest = last_asst + timedelta(seconds=rhythm)
    return (earliest - t).total_seconds()
