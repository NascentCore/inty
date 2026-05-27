"""In-process companion presence: coordinator state + session lifecycle across channels.

``CompanionPresenceCoordinator`` holds turn serialization, tool-background queues,
inner-tick coordinates, and overlap guards (channel-agnostic). ``CompanionPresenceSession``
binds a :class:`~app.services.companion_presence.downlink.CompanionChannelDownlink` and
runs the inner-tick poll worker skeleton; transport adapters materialize
:class:`~app.services.companion_presence.downlink.CompanionDownlink` events.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from app.core.companion_harness.companion.turn_routes import (
    BootstrapInterimOutput,
    BootstrapInterimOutputSink,
)
from app.core.companion_harness.tools.tool_background import ToolOutputEvent
from app.services.companion_presence.downlink import (
    CompanionChannelDownlink,
    bootstrap_interim_downlink,
)

InnerTickPollRunner = Callable[[dict[str, Any]], Awaitable[None]]


def apply_companion_inner_tick_coords(
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


@dataclass
class CompanionPresenceCoordinator:
    """Channel-agnostic companion invariants for one signed-on (user, agent, chat) presence."""

    loop: asyncio.AbstractEventLoop
    # TODO(tool-bg-idle-starves-user-chat): Serializes greeting, user chat, and inner-tick on
    # one presence. See companion websocket_coordinator module docstring / issues #3113 #3123.
    turn_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    background_events: asyncio.Queue[ToolOutputEvent] = field(
        default_factory=asyncio.Queue
    )
    bootstrap_interim_events: asyncio.Queue[BootstrapInterimOutput] = field(
        default_factory=asyncio.Queue
    )
    foreground_pending: dict[str, dict[str, Any]] = field(default_factory=dict)
    inner_tick_context: dict[str, Any] = field(default_factory=dict)
    _inner_tick_proactive_tool_bg_idle: threading.Event | None = field(
        default=None, repr=False
    )
    _implicit_greeting_turn_task: asyncio.Task[Any] | None = field(
        default=None, repr=False
    )

    @classmethod
    def for_current_loop(cls) -> CompanionPresenceCoordinator:
        return cls.for_loop(asyncio.get_running_loop())

    @classmethod
    def for_loop(cls, loop: asyncio.AbstractEventLoop) -> CompanionPresenceCoordinator:
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
        apply_companion_inner_tick_coords(
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
class CompanionPresenceSession:
    """One companion presence: coordinator + channel downlink + inner-tick worker."""

    downlink: CompanionChannelDownlink
    coordinator: CompanionPresenceCoordinator
    _inner_tick_stop: asyncio.Event = field(repr=False)
    _inner_tick_task: asyncio.Task[None] | None = field(default=None, repr=False)

    @classmethod
    def create(
        cls,
        *,
        downlink: CompanionChannelDownlink,
        loop: asyncio.AbstractEventLoop,
    ) -> CompanionPresenceSession:
        return cls(
            downlink=downlink,
            coordinator=CompanionPresenceCoordinator.for_loop(loop),
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
        if self._inner_tick_task is not None and (not self._inner_tick_task.done()):
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
                inner_tick_snapshot: dict[str, Any] | None = None
                async with self.coordinator.turn_lock:
                    inner_tick_snapshot = (
                        self.coordinator.snapshot_inner_tick_coords()
                    )
                    if inner_tick_snapshot is not None:
                        self.coordinator.clear_inner_tick_proactive_tool_bg_idle_if_idle()
                if inner_tick_snapshot is None:
                    continue
                await run_one_poll(inner_tick_snapshot)

        self._inner_tick_stop.clear()
        self._inner_tick_task = asyncio.create_task(
            _worker(),
            name="companion_presence_inner_tick",
        )

    async def stop(self) -> None:
        self._inner_tick_stop.set()
        task = self._inner_tick_task
        if task is not None and (not task.done()):
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        self._inner_tick_task = None
        await self.cancel_implicit_greeting_if_running()
