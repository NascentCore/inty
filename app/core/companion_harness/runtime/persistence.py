"""Persistence protocol for companion runtime turns.

The runtime produces a structured turn result before the hosting surface decides
where to store it. This module defines that narrow persistence seam so WebSocket,
test, and tool-driven surfaces can share the same turn execution contract while
keeping storage policy outside the runtime.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Protocol

from app.core.companion_harness.contracts.turn import TurnInput, TurnOutput


class TurnPersistence(Protocol):
    """Storage adapter called after a companion runtime turn finishes."""

    async def persist(
        self,
        *,
        turn_input: TurnInput,
        turn_output: TurnOutput,
    ) -> dict[str, Any] | None:
        """Persist a turn and return optional metadata for the caller."""
        ...


@dataclass(frozen=True)
class CallableTurnPersistence:
    """Adapter that accepts either synchronous or asynchronous persistence."""

    persist_fn: Callable[
        [TurnInput, TurnOutput],
        dict[str, Any] | None | Awaitable[dict[str, Any] | None],
    ]

    async def persist(
        self,
        *,
        turn_input: TurnInput,
        turn_output: TurnOutput,
    ) -> dict[str, Any] | None:
        """Call the configured persistence function and await it when needed."""
        result = self.persist_fn(turn_input, turn_output)
        if inspect.isawaitable(result):
            return await result
        return result
