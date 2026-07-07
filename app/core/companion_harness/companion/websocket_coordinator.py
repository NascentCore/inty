"""WebSocket-specific companion coordinator and per-connection inflight turn tracking.

``CompanionWebSocketCoordinator`` extends :class:`~app.services.agentic_companion.session.Coordinator`
for ``/api/v1/chat/ws`` presence state. Channel-agnostic state lives in
``app.services.agentic_companion.session``.

Each ``chat_completions_websocket`` accept creates one coordinator (one presence wire).
Prototype: that accept **is** the only wire for the paired user (no multi-tab).
Turns serialize on scope ``CompanionSession.turn_lock`` (#3272). See
``session.Coordinator`` and ``companion_harness`` AGENTS.md「Concurrency (prototype)」.

TODO(ws-disconnect-lifecycle): https://github.com/NascentCore/inty/issues/3256 — on shutdown — #3256
or WebSocket session end, do not cancel in-flight turns; persist-first with delivery state,
mark undelivered, replay after ``user_signed_on``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from dataclasses import dataclass, field
from typing import Any, TypeVar

from app.services.agentic_companion.session import (
    Coordinator,
    apply_inner_tick_coords,
)

_ChatWsInflightTurnResult = TypeVar("_ChatWsInflightTurnResult")


def apply_companion_ws_inner_tick_coords(
    inner_tick_ctx: dict[str, Any],
    *,
    user_id: Any,
    agent_id: str,
    chat_id: Any,
) -> None:
    """Alias for :func:`apply_inner_tick_coords` (``chat_ws`` import path)."""
    apply_inner_tick_coords(
        inner_tick_ctx,
        user_id=user_id,
        agent_id=agent_id,
        chat_id=chat_id,
    )


@dataclass
class ChatWsInflightTurnTracker:
    """Per ``/api/v1/chat/ws`` connection: companion turns that must stop on disconnect or process shutdown."""

    _tasks: set[asyncio.Task[Any]] = field(default_factory=set)

    def spawn(
        self,
        coro: Coroutine[Any, Any, _ChatWsInflightTurnResult],
        *,
        name: str,
    ) -> asyncio.Task[_ChatWsInflightTurnResult]:
        task = asyncio.create_task(coro, name=name)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    async def cancel_all(self) -> None:
        # TODO(ws-disconnect-lifecycle): #3256 — replace cancel with detach + persist-first delivery state.
        pending = [t for t in list(self._tasks) if not t.done()]
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)


class ChatWsInflightShutdownRegistry:
    """Process-wide index of live :class:`ChatWsInflightTurnTracker` instances for shutdown."""

    _trackers: list[ChatWsInflightTurnTracker] = []

    @classmethod
    def register(cls, tracker: ChatWsInflightTurnTracker) -> None:
        cls._trackers.append(tracker)

    @classmethod
    def unregister(cls, tracker: ChatWsInflightTurnTracker) -> None:
        try:
            cls._trackers.remove(tracker)
        except ValueError:
            pass

    @classmethod
    async def cancel_all_registered(cls) -> None:
        for tracker in list(cls._trackers):
            await tracker.cancel_all()


@dataclass
class CompanionWebSocketCoordinator(Coordinator):
    """``/api/v1/chat/ws`` coordinator: presence state for one WebSocket accept."""

    @classmethod
    def for_current_loop(cls) -> CompanionWebSocketCoordinator:
        return cls(loop=asyncio.get_running_loop())
