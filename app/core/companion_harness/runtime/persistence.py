from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Protocol

from app.core.companion_harness.contracts.turn import TurnInput, TurnOutput


class TurnPersistence(Protocol):
    async def persist(
        self,
        *,
        turn_input: TurnInput,
        turn_output: TurnOutput,
    ) -> dict[str, Any] | None: ...


@dataclass(frozen=True)
class CallableTurnPersistence:
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
        result = self.persist_fn(turn_input, turn_output)
        if inspect.isawaitable(result):
            return await result
        return result
