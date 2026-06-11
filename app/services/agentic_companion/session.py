"""In-process agentic companion: coordinator state + session lifecycle across channels.

``Coordinator`` holds turn serialization, tool-background queues,
inner-tick coordinates, and overlap guards (channel-agnostic). ``Session``
binds a :class:`~app.services.agentic_companion.downlink.ChannelDownlink` and
runs the inner-tick poll worker skeleton; transport adapters materialize
:class:`~app.services.agentic_companion.downlink.Downlink` events.

Production companion user paths: **WebSocket + Weixin only**; no HTTP chat unless
explicitly added later (must share scope turn serialization if it is).
Design focus: coherent scope state + behavior display (text / image / voice-audio).

Concurrency vocabulary (human terms — three layers, not interchangeable):

- **Scope** — one chat archive: ``(user_id, agent_id, chat_id)``. One ``CompanionSession``
  and one ``MemoryStore`` per scope in-process.
- **Presence** — one live wire to the user (a WebSocket accept or Weixin in-process session).
  Prototype (**``companion_harness`` AGENTS.md**): **one presence per paired user** — not
  multiple tabs / multiple wires. Each presence has one ``Coordinator`` and one ``turn_lock``.
- **``turn_lock`` (presence level)** — "on this phone line, handle one turn at a time": user
  message, greeting, inner-tick fire (including dreaming), tool-background downlink. Prototype
  does not model a second tab on the same scope; no extra scope mutex for cross-tab races.

Post-prototype: enforce single-presence on ``accept()`` (#3272 —
https://github.com/NascentCore/inty/issues/3272) and hoist ``turn_lock`` to
``CompanionSession`` — ``chat_ws`` TODO(companion-ws-single-presence). Scope-level inner-tick
worker (dreaming + maintenance/autonomy without signed-on user): #3255 /
TODO(scope-inner-tick-worker) in ``inner_tick_poll``. Presence poll keeps delivery tracks only
(proactive, scheduled).
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.companion_harness.companion.turn_routes import (
    BootstrapInterimOutput,
    BootstrapInterimOutputSink,
)
from app.core.companion_harness.tools.tool_background import ToolOutputEvent
from app.services.agentic_companion.downlink import (
    ChannelDownlink,
    bootstrap_interim_downlink,
)

InnerTickPollRunner = Callable[[dict[str, Any]], Awaitable[None]]


class InnerTickCoords(BaseModel):
    """Signed-on inner-tick scope triple from ``Coordinator.inner_tick_context``."""

    model_config = ConfigDict(frozen=True)

    user_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    chat_id: str = Field(min_length=1)

    @classmethod
    def from_context(cls, ctx: dict[str, Any]) -> InnerTickCoords | None:
        """Parse poll coordinates; ``None`` when any required field is missing."""
        user_id = str(ctx.get("user_id") or "").strip()
        agent_id = str(ctx.get("agent_id") or "").strip()
        chat_id_raw = ctx.get("chat_id")
        if not user_id or not agent_id or chat_id_raw is None:
            return None
        return cls(
            user_id=user_id,
            agent_id=agent_id,
            chat_id=str(chat_id_raw),
        )


def apply_inner_tick_coords(
    inner_tick_ctx: dict[str, Any],
    *,
    user_id: Any,
    agent_id: str,
    chat_id: Any,
) -> None:
    """Replace inner-tick coordinates while preserving same-session maintenance throttle."""
    prev_user = inner_tick_ctx.get("user_id")
    prev_agent = inner_tick_ctx.get("agent_id")
    prev_chat = inner_tick_ctx.get("chat_id")
    prev_mono = inner_tick_ctx.get("_last_maintenance_inner_tick_monotonic")
    prev_line_count = inner_tick_ctx.get(
        "_last_maintenance_transcript_line_count"
    )
    prev_autonomy_mono = inner_tick_ctx.get(
        "_last_autonomy_inner_tick_monotonic"
    )
    prev_autonomy_line_count = inner_tick_ctx.get(
        "_last_autonomy_transcript_line_count"
    )
    inner_tick_ctx.clear()
    inner_tick_ctx.update(
        {"user_id": user_id, "agent_id": agent_id, "chat_id": chat_id}
    )
    same_coords = (
        str(prev_user or "") == str(user_id or "")
        and str(prev_agent or "") == str(agent_id or "")
        and str(prev_chat or "") == str(chat_id or "")
    )
    if same_coords and prev_mono is not None:
        inner_tick_ctx["_last_maintenance_inner_tick_monotonic"] = prev_mono
    if same_coords and prev_line_count is not None:
        inner_tick_ctx["_last_maintenance_transcript_line_count"] = (
            prev_line_count
        )
    if same_coords and prev_autonomy_mono is not None:
        inner_tick_ctx["_last_autonomy_inner_tick_monotonic"] = (
            prev_autonomy_mono
        )
    if same_coords and prev_autonomy_line_count is not None:
        inner_tick_ctx["_last_autonomy_transcript_line_count"] = (
            prev_autonomy_line_count
        )


@dataclass
class Coordinator:
    """Channel-agnostic companion invariants for one signed-on (user, agent, chat) presence."""

    loop: asyncio.AbstractEventLoop
    # Presence-level turn serializer (one asyncio.Lock per WS / Weixin connection).
    # Holds while one turn runs on *this wire*; does not serialize another tab on the same scope.
    # TODO(tool-bg-idle-starves-user-chat): See websocket_coordinator / issues #3113 #3123.
    turn_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    background_events: asyncio.Queue[ToolOutputEvent] = field(
        default_factory=asyncio.Queue
    )
    # TODO(companion-ws-bootstrap-downlink): channel-agnostic queue unused on WS; collapse with downlink. #3209
    bootstrap_interim_events: asyncio.Queue[BootstrapInterimOutput] = field(
        default_factory=asyncio.Queue
    )
    # TODO(data-type-abstraction): Change this to a dataclass.
    foreground_pending: dict[str, dict[str, Any]] = field(default_factory=dict)
    # TODO(data-type-abstraction): Change this to a dataclass.
    inner_tick_context: dict[str, Any] = field(default_factory=dict)
    # TODO(#3314): Replace per-track lingering-work fields with one lifecycle-owned
    # background work registry / structured-concurrency scope.
    _inner_tick_proactive_tool_bg_idle: threading.Event | None = field(
        default=None, repr=False
    )
    _inner_tick_autonomy_tool_bg_idle: threading.Event | None = field(
        default=None, repr=False
    )
    _implicit_greeting_turn_task: asyncio.Task[Any] | None = field(
        default=None, repr=False
    )

    @classmethod
    def for_current_loop(cls) -> Coordinator:
        return cls.for_loop(asyncio.get_running_loop())

    @classmethod
    def for_loop(cls, loop: asyncio.AbstractEventLoop) -> Coordinator:
        return cls(loop=loop)

    def background_sink(self, event: ToolOutputEvent) -> None:
        """Thread-safe sink passed into tool_background jobs."""
        self.loop.call_soon_threadsafe(self.background_events.put_nowait, event)

    def bootstrap_interim_output_sink(self) -> BootstrapInterimOutputSink:
        """Async sink for bootstrap sync tool-loop rounds (queues ``BootstrapInterimOutput``)."""

        async def _sink(ev: BootstrapInterimOutput) -> None:
            await self.bootstrap_interim_events.put(ev)

        return _sink

    def set_foreground_pending(
        self, user_msg_uuid: str, context: dict[str, Any]
    ) -> None:
        self.foreground_pending[user_msg_uuid] = context

    def update_foreground_pending(
        self, user_msg_uuid: str, updates: dict[str, Any]
    ) -> None:
        if user_msg_uuid in self.foreground_pending:
            self.foreground_pending[user_msg_uuid].update(updates)

    def pop_foreground_pending(
        self, user_msg_uuid: str
    ) -> dict[str, Any] | None:
        return self.foreground_pending.pop(user_msg_uuid, None)

    def remove_foreground_pending(self, user_msg_uuid: str) -> None:
        self.foreground_pending.pop(user_msg_uuid, None)

    def has_foreground_pending(self, user_msg_uuid: str) -> bool:
        return user_msg_uuid in self.foreground_pending

    def store_inner_tick_coords(
        self,
        *,
        user_id: Any,
        agent_id: str,
        chat_id: Any,
    ) -> None:
        apply_inner_tick_coords(
            self.inner_tick_context,
            user_id=user_id,
            agent_id=agent_id,
            chat_id=chat_id,
        )

    def snapshot_inner_tick_coords(self) -> dict[str, Any] | None:
        user_id = str(self.inner_tick_context.get("user_id") or "").strip()
        agent_id = str(self.inner_tick_context.get("agent_id") or "").strip()
        chat_id = self.inner_tick_context.get("chat_id")
        if not user_id or not agent_id or chat_id is None:
            return None
        return {"user_id": user_id, "agent_id": agent_id, "chat_id": chat_id}

    def last_maintenance_inner_tick_monotonic(self) -> Any:
        return self.inner_tick_context.get(
            "_last_maintenance_inner_tick_monotonic"
        )

    def last_maintenance_transcript_line_count(self) -> int | None:
        raw = self.inner_tick_context.get(
            "_last_maintenance_transcript_line_count"
        )
        if raw is None:
            return None
        return int(raw)

    def mark_maintenance_inner_tick_fired(
        self,
        monotonic_time: float,
        transcript_line_count: int,
    ) -> None:
        self.inner_tick_context["_last_maintenance_inner_tick_monotonic"] = (
            monotonic_time
        )
        self.inner_tick_context["_last_maintenance_transcript_line_count"] = (
            transcript_line_count
        )

    def bind_inner_tick_proactive_tool_bg_idle(
        self, ev: threading.Event | None
    ) -> None:
        """Track ``CompanionSession.tool_bg_idle`` after proactive inner-tick starts async tool_bg."""
        self._inner_tick_proactive_tool_bg_idle = ev

    def clear_inner_tick_proactive_tool_bg_idle_if_idle(self) -> None:
        idle_ev = self._inner_tick_proactive_tool_bg_idle
        if idle_ev is not None and idle_ev.is_set():
            self._inner_tick_proactive_tool_bg_idle = None

    def inner_tick_proactive_tool_bg_still_running(self) -> bool:
        idle_ev = self._inner_tick_proactive_tool_bg_idle
        return idle_ev is not None and (not idle_ev.is_set())

    def bind_inner_tick_autonomy_tool_bg_idle(
        self, ev: threading.Event | None
    ) -> None:
        """Track ``CompanionSession.tool_bg_idle`` after autonomy inner-tick starts async tool_bg."""
        self._inner_tick_autonomy_tool_bg_idle = ev

    def clear_inner_tick_autonomy_tool_bg_idle_if_idle(self) -> None:
        idle_ev = self._inner_tick_autonomy_tool_bg_idle
        if idle_ev is not None and idle_ev.is_set():
            self._inner_tick_autonomy_tool_bg_idle = None

    def inner_tick_autonomy_tool_bg_still_running(self) -> bool:
        idle_ev = self._inner_tick_autonomy_tool_bg_idle
        return idle_ev is not None and (not idle_ev.is_set())

    def last_autonomy_inner_tick_monotonic(self) -> Any:
        return self.inner_tick_context.get(
            "_last_autonomy_inner_tick_monotonic"
        )

    def last_autonomy_transcript_line_count(self) -> int | None:
        raw = self.inner_tick_context.get(
            "_last_autonomy_transcript_line_count"
        )
        if raw is None:
            return None
        return int(raw)

    def mark_autonomy_inner_tick_fired(
        self,
        monotonic_time: float,
        transcript_line_count: int,
    ) -> None:
        self.inner_tick_context["_last_autonomy_inner_tick_monotonic"] = (
            monotonic_time
        )
        self.inner_tick_context["_last_autonomy_transcript_line_count"] = (
            transcript_line_count
        )

    def inner_tick_maintenance_foreground_pending(self) -> bool:
        return any(
            bool(ctx.get("ws_inner_tick_maintenance"))
            for ctx in self.foreground_pending.values()
        )

    def register_implicit_greeting_turn(self, task: asyncio.Task[Any]) -> None:
        """Track the detached ``user_signed_on`` greeting task for user-chat preemption."""
        self._implicit_greeting_turn_task = task

        def _on_done(done_task: asyncio.Task[Any]) -> None:
            if self._implicit_greeting_turn_task is done_task:
                self._implicit_greeting_turn_task = None

        task.add_done_callback(_on_done)

    async def cancel_implicit_greeting_turn_if_running(self) -> bool:
        """Cancel in-flight implicit greeting so user chat can take ``turn_lock``."""
        task = self._implicit_greeting_turn_task
        if task is None or task.done():
            return False
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        return True


@dataclass
class Session:
    """One companion presence: coordinator + channel downlink + inner-tick worker."""

    downlink: ChannelDownlink
    coordinator: Coordinator
    _inner_tick_stop: asyncio.Event = field(repr=False)
    _inner_tick_task: asyncio.Task[None] | None = field(
        default=None, repr=False
    )

    @classmethod
    def create(
        cls,
        *,
        downlink: ChannelDownlink,
        loop: asyncio.AbstractEventLoop,
    ) -> Session:
        return cls(
            downlink=downlink,
            coordinator=Coordinator.for_loop(loop),
            _inner_tick_stop=asyncio.Event(),
        )

    @classmethod
    def from_coordinator(
        cls,
        *,
        downlink: ChannelDownlink,
        coordinator: Coordinator,
    ) -> Session:
        """Bind an existing coordinator (e.g. ``CompanionWebSocketCoordinator``) to a channel downlink."""
        assert downlink is not None
        assert coordinator is not None
        return cls(
            downlink=downlink,
            coordinator=coordinator,
            _inner_tick_stop=asyncio.Event(),
        )

    def store_sign_on_coords(
        self,
        *,
        user_id: Any,
        agent_id: str,
        chat_id: Any,
    ) -> None:
        self.coordinator.store_inner_tick_coords(
            user_id=user_id,
            agent_id=agent_id,
            chat_id=chat_id,
        )

    def sign_out(self) -> None:
        self.coordinator.inner_tick_context.clear()

    async def cancel_implicit_greeting_if_running(self) -> bool:
        return await self.coordinator.cancel_implicit_greeting_turn_if_running()

    def background_sink(self, event: ToolOutputEvent) -> None:
        self.coordinator.background_sink(event)

    async def deliver_bootstrap_interim(
        self, interim: BootstrapInterimOutput
    ) -> None:
        # TODO(companion-ws-bootstrap-downlink): WS downlink must handle BOOTSTRAP_INTERIM before this is wired. #3209
        await self.downlink.deliver(
            bootstrap_interim_downlink(interim=interim),
        )

    async def start_inner_tick_worker(
        self,
        *,
        poll_seconds: float,
        run_one_poll: InnerTickPollRunner,
    ) -> None:
        assert poll_seconds > 0.0
        if self._inner_tick_task is not None and (
            not self._inner_tick_task.done()
        ):
            return

        async def _worker() -> None:
            while not self._inner_tick_stop.is_set():
                try:
                    await asyncio.wait_for(
                        self._inner_tick_stop.wait(), timeout=poll_seconds
                    )
                    break
                except asyncio.TimeoutError:
                    pass
                if self._inner_tick_stop.is_set():
                    break
                inner_tick_snapshot: dict[str, Any] | None = None
                async with self.coordinator.turn_lock:
                    if self._inner_tick_stop.is_set():
                        break
                    inner_tick_snapshot = (
                        self.coordinator.snapshot_inner_tick_coords()
                    )
                    if inner_tick_snapshot is not None:
                        # TODO(#3314): Move opportunistic cleanup out of the poll loop;
                        # completed background work should prune itself via registry callbacks.
                        self.coordinator.clear_inner_tick_proactive_tool_bg_idle_if_idle()
                        self.coordinator.clear_inner_tick_autonomy_tool_bg_idle_if_idle()
                if inner_tick_snapshot is None or self._inner_tick_stop.is_set():
                    continue
                await run_one_poll(inner_tick_snapshot)

        self._inner_tick_stop.clear()
        self._inner_tick_task = asyncio.create_task(
            _worker(),
            name="inner_tick",
        )

    async def stop(self) -> None:
        self._inner_tick_stop.set()
        task = self._inner_tick_task
        self._inner_tick_task = None
        if task is not None and (not task.done()):
            await asyncio.gather(task, return_exceptions=True)
        # TODO(#3314): Session shutdown should cancel/drain every registered
        # lifecycle child, not only the poll worker and implicit greeting task.
        await self.cancel_implicit_greeting_if_running()
