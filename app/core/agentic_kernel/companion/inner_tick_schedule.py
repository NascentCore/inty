"""REPL idle inner tick: fixed poll chunk + min gap between successful ticks."""

from __future__ import annotations

import os
import time
from pathlib import Path

from .memory_registry import get_memory_store
from .models import (
    load_transcript_from_store,
    transcript_without_trailing_presence_signals,
)

REPL_IDLE_MAX_SLEEP_CHUNK_SEC = 3600.0

_DISABLED_INNER_TICK_WAIT_SEC = 86400.0 * 365.0

_INNER_TICK_BLOCKED_MAX_SLEEP_SEC = 60.0

_DEFAULT_INNER_TICK_SEC = 90.0
_DEFAULT_MIN_GAP_SEC = 120.0
_DEFAULT_MIN_TRANSCRIPT_MSGS = 2


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
    return _env_float("INTY_V2_PROTO_INNER_TICK_MIN_GAP_SEC", _DEFAULT_MIN_GAP_SEC)


def next_inner_tick_wait_seconds(
    workspace: Path,
    *,
    last_inner_fire_monotonic: float | None,
    now_monotonic: float | None = None,
) -> float:
    if not inner_tick_enabled_from_env():
        return _DISABLED_INNER_TICK_WAIT_SEC

    now = now_monotonic if now_monotonic is not None else time.monotonic()
    root = workspace.resolve()
    store = get_memory_store(root)
    msgs = transcript_without_trailing_presence_signals(
        load_transcript_from_store(store, "transcript.jsonl")
    )
    min_lines = _env_int(
        "INTY_V2_PROTO_INNER_TICK_MIN_TRANSCRIPT_MSGS",
        _DEFAULT_MIN_TRANSCRIPT_MSGS,
    )
    poll = inner_tick_poll_seconds()
    blocked_sleep = min(_INNER_TICK_BLOCKED_MAX_SLEEP_SEC, poll)
    if len(msgs) < min_lines:
        return blocked_sleep

    if not msgs or msgs[-1].role != "assistant":
        return blocked_sleep

    min_gap = inner_tick_min_gap_seconds()
    if last_inner_fire_monotonic is None:
        return 0.0
    elapsed = now - last_inner_fire_monotonic
    remain = min_gap - elapsed
    if remain <= 0.0:
        return 0.0
    return min(remain, poll)
