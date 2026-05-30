"""Maintenance and REPL-prototype inner-tick wait helpers (poll chunk + min gap).

TODO(inner-tick-autonomy): Rename maintenance scheduling to autonomy after inner-tick scope shrinks
to ai_private-only; align ``companion_ws_maintenance_inner_tick_*`` config keys and coordinator
monotonic fields.

WebSocket **proactive chat rhythm** lives in ``proactive_chat.py``;
the unified WS worker fires scheduled / proactive / maintenance
on ``companion_ws_proactive_chat_poll_seconds``.

See ``docs/companion_harness/INNER_TICK_SCHEDULING.md`` for human-facing scheduling semantics.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

from app.core.companion_harness.memory.memory_store import MemoryStore
from .models import (
    ChatMessage,
    load_context_meta,
    load_transcript_from_store,
    transcript_without_trailing_presence_signals,
)

REPL_IDLE_MAX_SLEEP_CHUNK_SEC = 3600.0

_DISABLED_INNER_TICK_WAIT_SEC = 86400.0 * 365.0

_INNER_TICK_BLOCKED_MAX_SLEEP_SEC = 60.0

_DEFAULT_INNER_TICK_SEC = 90.0
_DEFAULT_MIN_GAP_SEC = 120.0
_DEFAULT_MIN_TRANSCRIPT_MSGS = 2


@dataclass(frozen=True)
class InnerTickScheduleOverrides:
    """Optional production overrides; when set, each field wins over ``INTY_V2_PROTO_*`` env."""

    enabled: bool | None = None
    min_gap_seconds: float | None = None
    poll_seconds: float | None = None
    min_transcript_msgs: int | None = None


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return float(str(raw).strip())


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return int(str(raw).strip())


def inner_tick_enabled_from_env() -> bool:
    raw = os.environ.get("INTY_V2_PROTO_INNER_TICK_ENABLED")
    if raw is None or not str(raw).strip():
        return True
    s = str(raw).strip().lower()
    if s in ("0", "false", "no", "off"):
        return False
    return True


def inner_tick_poll_seconds() -> float:
    return _env_float("INTY_V2_PROTO_INNER_TICK_SEC", _DEFAULT_INNER_TICK_SEC)


def inner_tick_min_gap_seconds() -> float:
    return _env_float(
        "INTY_V2_PROTO_INNER_TICK_MIN_GAP_SEC", _DEFAULT_MIN_GAP_SEC
    )


def _maintenance_transcript_messages(store: MemoryStore) -> list[ChatMessage]:
    """``transcript.jsonl`` rows with trailing presence user lines stripped (maintenance gate view)."""
    return transcript_without_trailing_presence_signals(
        load_transcript_from_store(store, "transcript.jsonl")
    )


def maintenance_transcript_line_count(store: MemoryStore) -> int:
    """Line count for ``transcript.jsonl`` (presence tail stripped), for maintenance skip."""
    return len(_maintenance_transcript_messages(store))


def transcript_tail_message_uuid(store: MemoryStore) -> str | None:
    """``uuid`` of the last ``transcript.jsonl`` row in the maintenance gate view.

    Maintenance turns persist to ``transcript_inner_tick.jsonl``
    (TODO(rename-memory-doc): ``transcript_inner_tick_maintenance.jsonl``); this reflects main-track
    state only (same source as ``next_inner_tick_wait_seconds``).
    """
    msgs = _maintenance_transcript_messages(store)
    if not msgs:
        return None
    tail_uuid = msgs[-1].uuid
    if tail_uuid is None or not str(tail_uuid).strip():
        return None
    return str(tail_uuid).strip()


def next_inner_tick_wait_seconds(
    store: MemoryStore,
    *,
    last_inner_fire_monotonic: float | None,
    last_maintenance_transcript_line_count: int | None,
    now_monotonic: float | None = None,
    overrides: InnerTickScheduleOverrides | None = None,
) -> float:
    enabled = inner_tick_enabled_from_env()
    if overrides is not None and overrides.enabled is not None:
        enabled = overrides.enabled
    if not enabled:
        return _DISABLED_INNER_TICK_WAIT_SEC

    if not load_context_meta(
        store=store
    ).workspace_bootstrap_user_interactive_completed:
        return _DISABLED_INNER_TICK_WAIT_SEC

    now = now_monotonic if now_monotonic is not None else time.monotonic()
    msgs = _maintenance_transcript_messages(store)
    line_count = len(msgs)
    if last_maintenance_transcript_line_count is not None:
        if line_count <= last_maintenance_transcript_line_count:
            return _DISABLED_INNER_TICK_WAIT_SEC

    if overrides is not None and overrides.min_transcript_msgs is not None:
        min_lines = overrides.min_transcript_msgs
    else:
        min_lines = _env_int(
            "INTY_V2_PROTO_INNER_TICK_MIN_TRANSCRIPT_MSGS",
            _DEFAULT_MIN_TRANSCRIPT_MSGS,
        )

    poll = inner_tick_poll_seconds()
    if overrides is not None and overrides.poll_seconds is not None:
        poll = overrides.poll_seconds

    blocked_sleep = min(_INNER_TICK_BLOCKED_MAX_SLEEP_SEC, poll)
    if line_count < min_lines:
        return blocked_sleep

    if not msgs or msgs[-1].role != "assistant":
        return blocked_sleep

    min_gap = inner_tick_min_gap_seconds()
    if overrides is not None and overrides.min_gap_seconds is not None:
        min_gap = overrides.min_gap_seconds

    if last_inner_fire_monotonic is None:
        return 0.0
    elapsed = now - last_inner_fire_monotonic
    remain = min_gap - elapsed
    if remain <= 0.0:
        return 0.0
    return min(remain, poll)
