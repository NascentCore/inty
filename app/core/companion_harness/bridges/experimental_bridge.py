"""Used only in /experimental/agentic_ai_companion"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, cast

from app.core.companion_harness.contracts.turn import (
    MessageSnapshot,
    MessageRole,
    TurnInput,
    TurnOutput,
)
from app.core.companion_harness.runtime.persistence import CallableTurnPersistence
from app.core.companion_harness.runtime.turn_orchestrator import (
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


_ALLOWED_MESSAGE_ROLES: set[MessageRole] = {"system", "user", "assistant", "tool"}


def _to_message_snapshots(messages: list[dict[str, Any]]) -> list[MessageSnapshot]:
    out: list[MessageSnapshot] = []
    for index, row in enumerate(messages):
        role = row.get("role")
        if not isinstance(role, str):
            raise ValueError(
                f"invalid message role type at index={index}: expected str, got {type(role)!r}"
            )
        if role not in _ALLOWED_MESSAGE_ROLES:
            raise ValueError(f"invalid message role at index={index}: {role!r}")

        content = row.get("content", "")
        if not isinstance(content, str):
            raise ValueError(
                f"invalid message content type at index={index}: expected str, got {type(content)!r}"
            )
        name = row.get("name")
        if name is not None and not isinstance(name, str):
            raise ValueError(
                f"invalid message name type at index={index}: expected str | None, got {type(name)!r}"
            )
        tool_call_id = row.get("tool_call_id")
        if tool_call_id is not None and not isinstance(tool_call_id, str):
            raise ValueError(
                "invalid message tool_call_id type at index="
                f"{index}: expected str | None, got {type(tool_call_id)!r}"
            )
        out.append(
            MessageSnapshot(
                role=cast(MessageRole, role),
                content=content,
                name=name,
                tool_call_id=tool_call_id,
                metadata={
                    k: v
                    for k, v in row.items()
                    if k not in {"role", "content", "name", "tool_call_id"}
                },
            )
        )
    return out


def message_snapshots_to_dicts(messages: list[MessageSnapshot]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for message in messages:
        row: dict[str, Any] = {
            "role": message.role,
            "content": message.content,
        }
        if message.name is not None:
            row["name"] = message.name
        if message.tool_call_id is not None:
            row["tool_call_id"] = message.tool_call_id
        row.update(message.metadata)
        out.append(row)
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
    handle_response: Callable[[TurnInput, Any], TurnOutput | Awaitable[TurnOutput]],
    persist_fn: (
        Callable[
            [TurnInput, TurnOutput],
            dict[str, Any] | None | Awaitable[dict[str, Any] | None],
        ]
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
