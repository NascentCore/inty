"""Shim: implementation in app.core.agentic_kernel.companion.inner_tick_schedule."""

from __future__ import annotations

from app.core.agentic_kernel.companion.inner_tick_schedule import (
    REPL_IDLE_MAX_SLEEP_CHUNK_SEC,
    inner_tick_enabled_from_env,
    inner_tick_min_gap_seconds,
    inner_tick_poll_seconds,
    next_inner_tick_wait_seconds,
)

__all__ = [
    "REPL_IDLE_MAX_SLEEP_CHUNK_SEC",
    "inner_tick_enabled_from_env",
    "inner_tick_min_gap_seconds",
    "inner_tick_poll_seconds",
    "next_inner_tick_wait_seconds",
]
