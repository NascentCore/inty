"""Connection-scoped coordination state for production companion WebSocket turns.

The FastAPI endpoint owns transport, auth, persistence, and payload shaping. This module owns
the small set of per-connection companion invariants that must stay together: turn
serialization, background tool event delivery, foreground/background correlation,
inner-tick coordinates, and overlap guards when a prior inner-tick pass still has async
tool_background work in flight.

TODO(ws-disconnect-lifecycle): On server shutdown or WebSocket session end, do not cancel
in-flight companion turns. Let background tasks finish, persist produced messages to storage,
and mark them undelivered so the client can receive them after ``user_signed_on``.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Coroutine
from dataclasses import dataclass, field
from typing import Any, TypeVar

from app.core.companion_harness.tools.tool_background import ToolOutputEvent

_ChatWsInflightTurnResult = TypeVar("_ChatWsInflightTurnResult")


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
    """Process-wide index of live :class:`ChatWsInflightTurnTracker` instances for shutdown.

    **Usage** (one tracker per ``/api/v1/chat/ws`` connection):

    1. After opening the socket, ``tracker = ChatWsInflightTurnTracker()`` then
       ``ChatWsInflightShutdownRegistry.register(tracker)``.
    2. Wrap each detached companion turn (user message completion, ``user_signed_on``
       greeting, etc.) in ``tracker.spawn(coro, name=...)`` so disconnect/sign-out and
       process shutdown can cancel it.
    3. In the connection ``finally``, ``await tracker.cancel_all()`` then
       ``unregister(tracker)``.
    4. Register ``cancel_all_registered`` on app shutdown (see ``backend/inty/main.py``).

    **Interim behavior:** ``cancel_all`` / ``cancel_all_registered`` cancel tasks today.
    TODO(ws-disconnect-lifecycle): replace with detach + undelivered persistence (module
    docstring); this registry must follow the same lifecycle change as per-connection
    trackers.
    """

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
        # TODO(ws-disconnect-lifecycle): process shutdown — same as ``cancel_all`` (module docstring).
        for tracker in list(cls._trackers):
            await tracker.cancel_all()


def apply_companion_ws_inner_tick_coords(
    inner_tick_ctx: dict[str, Any],
    *,
    user_id: Any,
    agent_id: str,
    chat_id: Any,
) -> None:
    """Replace inner-tick coordinates while preserving same-session maintenance throttle.

    Shared by :class:`CompanionWebSocketCoordinator` and chat endpoints that hold the same
    logical dict (``companion_ws_inner_tick_ctx`` references ``inner_tick_context``).
    """
    prev_user = inner_tick_ctx.get("user_id")
    prev_agent = inner_tick_ctx.get("agent_id")
    prev_chat = inner_tick_ctx.get("chat_id")
    prev_mono = inner_tick_ctx.get("_last_maintenance_inner_tick_monotonic")
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


@dataclass
class CompanionWebSocketCoordinator:
    """State capsule for one ``/api/v1/chat/ws`` companion connection."""

    loop: asyncio.AbstractEventLoop
    # TODO(tool-bg-idle-starves-user-chat): Serializes greeting, USER_MESSAGE, and
    # proactive/maintenance inner-tick on one WebSocket. A holder blocked inside
    # run_turn on session tool_bg_idle (often after maintenance tool_bg_only) queues
    # later USER_MESSAGE with no chat reply until idle wait times out (~600s).
    # Intended: user chat preempts inner-tick or does not wait on maintenance tool_bg.
    # https://github.com/NascentCore/inty/issues/3113
    # https://github.com/NascentCore/inty/issues/3123 (tool_bg_idle while lock held)
    turn_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    background_events: asyncio.Queue[ToolOutputEvent] = field(
        default_factory=asyncio.Queue
    )
    foreground_pending: dict[str, dict[str, Any]] = field(default_factory=dict)
    inner_tick_context: dict[str, Any] = field(default_factory=dict)
    _ws_inner_tick_proactive_tool_bg_idle: threading.Event | None = field(
        default=None, repr=False
    )
    _implicit_greeting_turn_task: asyncio.Task[Any] | None = field(
        default=None, repr=False
    )

    @classmethod
    def for_current_loop(cls) -> "CompanionWebSocketCoordinator":
        return cls(loop=asyncio.get_running_loop())

    def background_sink(self, event: ToolOutputEvent) -> None:
        """Thread-safe sink passed into tool_background jobs."""
        self.loop.call_soon_threadsafe(self.background_events.put_nowait, event)

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
        apply_companion_ws_inner_tick_coords(
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

    def mark_maintenance_inner_tick_fired(self, monotonic_time: float) -> None:
        self.inner_tick_context["_last_maintenance_inner_tick_monotonic"] = (
            monotonic_time
        )

    def bind_ws_inner_tick_proactive_tool_bg_idle(
        self, ev: threading.Event | None
    ) -> None:
        """Track ``CompanionSession.tool_bg_idle`` after proactive inner-tick starts async tool_bg."""
        self._ws_inner_tick_proactive_tool_bg_idle = ev

    def clear_ws_inner_tick_proactive_tool_bg_idle_if_idle(self) -> None:
        idle_ev = self._ws_inner_tick_proactive_tool_bg_idle
        if idle_ev is not None and idle_ev.is_set():
            self._ws_inner_tick_proactive_tool_bg_idle = None

    def ws_inner_tick_proactive_tool_bg_still_running(self) -> bool:
        idle_ev = self._ws_inner_tick_proactive_tool_bg_idle
        return idle_ev is not None and (not idle_ev.is_set())

    def ws_inner_tick_maintenance_foreground_pending(self) -> bool:
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
