"""WebSocket-specific companion coordinator and per-connection inflight turn tracking.

``CompanionWebSocketCoordinator`` extends :class:`~app.services.agentic_companion.session.Coordinator`
with WS-only bootstrap deliver context and outbound queue binding. Channel-agnostic
state lives in ``app.services.agentic_companion.session``.

Each ``chat_completions_websocket`` accept creates one coordinator (one presence wire).
Prototype: that accept **is** the only wire for the paired user (no multi-tab).
Turns serialize on scope ``CompanionSession.turn_lock`` (#3272). See
``session.Coordinator`` and ``companion_harness`` AGENTS.md「Concurrency (prototype)」.

TODO(ws-disconnect-lifecycle): https://github.com/NascentCore/inty/issues/3256 — on shutdown — #3256
or WebSocket session end, do not cancel in-flight turns; persist-first with delivery state,
mark undelivered, replay after ``user_signed_on``.


TODO(companion-package-reorg): Move this module into a focused sub-package under companion_harness (see issue body for draft layout). — #3409
https://github.com/NascentCore/inty/issues/3409"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeVar

from app.core.companion_harness.companion.turn_routes import (
    BootstrapInterimOutput,
    BootstrapInterimOutputSink,
)
from app.services.agentic_companion.session import (
    Coordinator,
    apply_inner_tick_coords,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

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
class BootstrapInterimDeliverCtx:
    """Per user_chat turn: materialize ``BootstrapInterimOutput`` into WS + chat history."""

    db: "AsyncSession"
    agent_id: str
    session_id: str
    request: Any
    last_user_text: str
    effective_local_id: str | None
    outbound_queue: asyncio.Queue[Any]


@dataclass(frozen=True)
class BootstrapInterimQueued:
    """Queued interim round with deliver ctx captured at enqueue time."""

    ev: BootstrapInterimOutput
    ctx: BootstrapInterimDeliverCtx


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
    """``/api/v1/chat/ws`` coordinator: presence state plus WS bootstrap/outbound hooks."""

    # TODO(companion-ws-bootstrap-downlink): fold queue + deliver_ctx into session downlink. #3209 #3211 #3398
    bootstrap_interim_queued_events: asyncio.Queue[BootstrapInterimQueued] = (
        field(default_factory=asyncio.Queue)
    )
    bootstrap_interim_deliver_ctx: BootstrapInterimDeliverCtx | None = field(
        default=None, repr=False
    )
    outbound_queue: asyncio.Queue[Any] | None = field(default=None, repr=False)

    @classmethod
    def for_current_loop(cls) -> CompanionWebSocketCoordinator:
        return cls(loop=asyncio.get_running_loop())

    def set_bootstrap_interim_deliver_ctx(
        self, ctx: BootstrapInterimDeliverCtx
    ) -> None:
        self.bootstrap_interim_deliver_ctx = ctx

    def clear_bootstrap_interim_deliver_ctx(self) -> None:
        self.bootstrap_interim_deliver_ctx = None

    def bind_outbound_queue(self, queue: asyncio.Queue[Any]) -> None:
        self.outbound_queue = queue

    def bootstrap_interim_output_sink(self) -> BootstrapInterimOutputSink:
        """WS sink: queue ``BootstrapInterimQueued`` with captured deliver ctx."""
        # TODO(companion-ws-bootstrap-downlink): collapse with session downlink. #3209 #3398

        async def _sink(ev: BootstrapInterimOutput) -> None:
            ctx = self.bootstrap_interim_deliver_ctx
            assert ctx is not None
            await self.bootstrap_interim_queued_events.put(
                BootstrapInterimQueued(ev=ev, ctx=ctx)
            )

        return _sink
