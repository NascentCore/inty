"""Shared ``turn_lock`` scope for inner-tick activities."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.core.companion_harness.companion.manager import CompanionSession


@asynccontextmanager
async def inner_tick_turn_scope(
    *,
    session: CompanionSession,
) -> AsyncIterator[None]:
    """Acquire scope ``turn_lock`` for one inner-tick activity."""
    async with session.turn_lock:
        yield
