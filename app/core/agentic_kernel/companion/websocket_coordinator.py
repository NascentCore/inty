"""Connection-scoped coordination state for production companion WebSocket turns.

The FastAPI endpoint owns transport, auth, persistence, and payload shaping. This module owns
the small set of per-connection companion invariants that must stay together: turn
serialization, background tool event delivery, foreground/background correlation,
inner-tick coordinates, and overlap guards when a prior inner-tick pass still has async
tool_background work in flight.
"""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field
from typing import Any

from .tool_background import ToolOutputEvent


def apply_companion_ws_heartbeat_coords(
    hb_ctx: dict[str, Any],
    *,
    user_id: Any,
    agent_id: str,
    chat_id: Any,
) -> None:
    """Replace inner-tick coordinates while preserving same-session maintenance throttle.

    Shared by :class:`CompanionWebSocketCoordinator` and chat endpoints that hold the same
    logical dict (``companion_ws_heartbeat_ctx`` references ``heartbeat_context``).
    """
    prev_user = hb_ctx.get("user_id")
    prev_agent = hb_ctx.get("agent_id")
    prev_chat = hb_ctx.get("chat_id")
    prev_mono = hb_ctx.get("_last_maintenance_inner_tick_monotonic")
    hb_ctx.clear()
    hb_ctx.update({"user_id": user_id, "agent_id": agent_id, "chat_id": chat_id})
    same_coords = (
        str(prev_user or "") == str(user_id or "")
        and str(prev_agent or "") == str(agent_id or "")
        and str(prev_chat or "") == str(chat_id or "")
    )
    if same_coords and prev_mono is not None:
        hb_ctx["_last_maintenance_inner_tick_monotonic"] = prev_mono


@dataclass
class CompanionWebSocketCoordinator:
    """State capsule for one ``/api/v1/chat/ws`` companion connection."""

    loop: asyncio.AbstractEventLoop
    turn_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    background_events: asyncio.Queue[ToolOutputEvent] = field(
        default_factory=asyncio.Queue
    )
    foreground_pending: dict[str, dict[str, Any]] = field(default_factory=dict)
    heartbeat_context: dict[str, Any] = field(default_factory=dict)
    _ws_inner_tick_proactive_tool_bg_idle: threading.Event | None = field(
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

    def pop_foreground_pending(self, user_msg_uuid: str) -> dict[str, Any] | None:
        return self.foreground_pending.pop(user_msg_uuid, None)

    def remove_foreground_pending(self, user_msg_uuid: str) -> None:
        self.foreground_pending.pop(user_msg_uuid, None)

    def has_foreground_pending(self, user_msg_uuid: str) -> bool:
        return user_msg_uuid in self.foreground_pending

    def store_heartbeat_coords(
        self,
        *,
        user_id: Any,
        agent_id: str,
        chat_id: Any,
    ) -> None:
        apply_companion_ws_heartbeat_coords(
            self.heartbeat_context,
            user_id=user_id,
            agent_id=agent_id,
            chat_id=chat_id,
        )

    def snapshot_heartbeat_coords(self) -> dict[str, Any] | None:
        user_id = str(self.heartbeat_context.get("user_id") or "").strip()
        agent_id = str(self.heartbeat_context.get("agent_id") or "").strip()
        chat_id = self.heartbeat_context.get("chat_id")
        if not user_id or not agent_id or chat_id is None:
            return None
        return {"user_id": user_id, "agent_id": agent_id, "chat_id": chat_id}

    def last_maintenance_inner_tick_monotonic(self) -> Any:
        return self.heartbeat_context.get("_last_maintenance_inner_tick_monotonic")

    def mark_maintenance_inner_tick_fired(self, monotonic_time: float) -> None:
        self.heartbeat_context["_last_maintenance_inner_tick_monotonic"] = (
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
