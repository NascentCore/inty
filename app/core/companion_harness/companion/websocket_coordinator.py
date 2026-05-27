"""WebSocket-specific companion coordinator and per-connection inflight turn tracking.

``CompanionWebSocketCoordinator`` extends :class:`~app.services.companion_presence.session.CompanionPresenceCoordinator`
with WS-only bootstrap deliver context and outbound queue binding. Channel-agnostic
state lives in ``app.services.companion_presence.session``.

TODO(ws-disconnect-lifecycle): On server shutdown or WebSocket session end, do not cancel
in-flight companion turns. Let background tasks finish, persist produced messages to storage,
and mark them undelivered so the client can receive them after ``user_signed_on``.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Coroutine
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeVar

from app.core.companion_harness.companion.turn_routes import (
    BootstrapInterimOutput,
    BootstrapInterimOutputSink,
)
from app.services.companion_presence.session import (
    CompanionPresenceCoordinator,
    apply_companion_inner_tick_coords,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.chat import ChatCompletionRequest

_ChatWsInflightTurnResult = TypeVar("_ChatWsInflightTurnResult")


def apply_companion_ws_inner_tick_coords(
    inner_tick_ctx: dict[str, Any],
    *,
    user_id: Any,
    agent_id: str,
    chat_id: Any,
) -> None:
    """Alias for :func:`apply_companion_inner_tick_coords` (``chat_ws`` import path)."""
    apply_companion_inner_tick_coords(
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
    request: "ChatCompletionRequest"
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
        # TODO(ws-disconnect-lifecycle): replace cancel with detach + undelivered persistence (see module docstring).
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
class CompanionWebSocketCoordinator(CompanionPresenceCoordinator):
    """``/api/v1/chat/ws`` coordinator: presence state plus WS bootstrap/outbound hooks."""

    bootstrap_interim_queued_events: asyncio.Queue[BootstrapInterimQueued] = field(
        default_factory=asyncio.Queue
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

        async def _sink(ev: BootstrapInterimOutput) -> None:
            ctx = self.bootstrap_interim_deliver_ctx
            if ctx is None:
                return
            await self.bootstrap_interim_queued_events.put(
                BootstrapInterimQueued(ev=ev, ctx=ctx)
            )

        return _sink

    def bind_ws_inner_tick_proactive_tool_bg_idle(
        self, ev: threading.Event | None
    ) -> None:
        self.bind_inner_tick_proactive_tool_bg_idle(ev)

    def clear_ws_inner_tick_proactive_tool_bg_idle_if_idle(self) -> None:
        self.clear_inner_tick_proactive_tool_bg_idle_if_idle()

    def ws_inner_tick_proactive_tool_bg_still_running(self) -> bool:
        return self.inner_tick_proactive_tool_bg_still_running()

    def ws_inner_tick_maintenance_foreground_pending(self) -> bool:
        return self.inner_tick_maintenance_foreground_pending()
