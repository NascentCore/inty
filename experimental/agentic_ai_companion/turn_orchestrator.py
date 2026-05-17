"""通用回合编排骨架：仅供本实验包（async REPL）使用，不进入生产 WebSocket 主链路。"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from app.core.companion_harness.contracts.turn import TurnInput, TurnOutput
from app.core.companion_harness.runtime.persistence import TurnPersistence

PrepareTurnFn = Callable[[TurnInput], TurnInput | Awaitable[TurnInput]]
InvokeModelFn = Callable[[TurnInput], Any | Awaitable[Any]]
HandleResponseFn = Callable[
    [TurnInput, Any], TurnOutput | Awaitable[TurnOutput]
]


@dataclass(frozen=True)
class TurnOrchestratorResult:
    output: TurnOutput
    raw_response: Any
    persist_metadata: dict[str, Any] | None


async def _await_if_needed(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


class TurnOrchestrator:
    def __init__(
        self,
        *,
        prepare_turn: PrepareTurnFn,
        invoke_model: InvokeModelFn,
        handle_response: HandleResponseFn,
        persistence: TurnPersistence | None = None,
    ) -> None:
        self._prepare_turn = prepare_turn
        self._invoke_model = invoke_model
        self._handle_response = handle_response
        self._persistence = persistence

    async def run(self, turn_input: TurnInput) -> TurnOrchestratorResult:
        prepared_turn_input = await _await_if_needed(
            self._prepare_turn(turn_input)
        )
        raw_response = await _await_if_needed(
            self._invoke_model(prepared_turn_input)
        )
        output = await _await_if_needed(
            self._handle_response(prepared_turn_input, raw_response)
        )
        persist_metadata: dict[str, Any] | None = None
        if self._persistence is not None:
            persist_metadata = await self._persistence.persist(
                turn_input=prepared_turn_input,
                turn_output=output,
            )
        return TurnOrchestratorResult(
            output=output,
            raw_response=raw_response,
            persist_metadata=persist_metadata,
        )
