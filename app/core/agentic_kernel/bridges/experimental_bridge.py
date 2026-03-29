from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable

from app.core.agentic_kernel.contracts.turn import (
    MessageSnapshot,
    TurnInput,
    TurnOutput,
)
from app.core.agentic_kernel.runtime.persistence import CallableTurnPersistence
from app.core.agentic_kernel.runtime.turn_orchestrator import (
    TurnOrchestrator,
    TurnOrchestratorResult,
)


@dataclass(frozen=True)
class ExperimentalTurnBridgeInput:
    user_id: str
    session_id: str
    agent_id: str
    user_text: str
    history: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None


def _to_message_snapshots(messages: list[dict[str, Any]]) -> list[MessageSnapshot]:
    out: list[MessageSnapshot] = []
    for row in messages:
        role = str(row.get("role", "user"))
        if role not in {"system", "user", "assistant", "tool"}:
            role = "user"
        content = row.get("content")
        out.append(
            MessageSnapshot(
                role=role,  # type: ignore[arg-type]
                content=content if isinstance(content, str) else "",
                name=row.get("name") if isinstance(row.get("name"), str) else None,
                tool_call_id=(
                    row.get("tool_call_id")
                    if isinstance(row.get("tool_call_id"), str)
                    else None
                ),
                metadata={
                    k: v
                    for k, v in row.items()
                    if k not in {"role", "content", "name", "tool_call_id"}
                },
            )
        )
    return out


def build_turn_input(payload: ExperimentalTurnBridgeInput) -> TurnInput:
    return TurnInput(
        user_id=payload.user_id,
        session_id=payload.session_id,
        agent_id=payload.agent_id,
        user_text=payload.user_text,
        history=_to_message_snapshots(payload.history or []),
        metadata=payload.metadata or {},
    )


async def run_experimental_turn(
    *,
    payload: ExperimentalTurnBridgeInput,
    prepare_turn: Callable[[TurnInput], TurnInput | Awaitable[TurnInput]],
    invoke_model: Callable[[TurnInput], Any | Awaitable[Any]],
    handle_response: Callable[
        [TurnInput, Any], TurnOutput | Awaitable[TurnOutput]
    ],
    persist_fn: (
        Callable[[TurnInput, TurnOutput], dict[str, Any] | None | Awaitable[dict[str, Any] | None]]
        | None
    ) = None,
) -> TurnOrchestratorResult:
    persistence = None
    if persist_fn is not None:
        persistence = CallableTurnPersistence(persist_fn=persist_fn)
    orchestrator = TurnOrchestrator(
        prepare_turn=prepare_turn,
        invoke_model=invoke_model,
        handle_response=handle_response,
        persistence=persistence,
    )
    return await orchestrator.run(build_turn_input(payload))


def default_workspace_payload(
    *,
    workspace: Path,
    user_text: str,
    history: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> ExperimentalTurnBridgeInput:
    ws = workspace.resolve()
    return ExperimentalTurnBridgeInput(
        user_id=f"workspace:{ws.name}",
        session_id=str(ws),
        agent_id="experimental",
        user_text=user_text,
        history=history,
        metadata=metadata or {},
    )
