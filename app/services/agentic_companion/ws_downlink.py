"""WebSocket downlink adapter: tool-background ``Downlink`` → outbound queue.

Bootstrap interim rounds use ``CompanionWebSocketCoordinator.bootstrap_interim_queued_events``
and ``chat_ws._companion_ws_bootstrap_interim_consumer``. Inner-tick assistant frames use
``inner_tick_fire`` + ``deliver_inner_tick_assistant``.

TODO(companion-ws-outbound-unify): Route bootstrap + inner-tick through this adapter so
``chat_ws`` has one downlink → ``outbound_queue`` contract. #3209 #3210 #3211 #3398
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from app.core.companion_harness.tools.tool_background import ToolOutputEvent
from app.services.agentic_companion.downlink import (
    Downlink,
    DownlinkKind,
    downlink_delivers_user_visible_text,
)
from app.services.ws_session_messages import WsOutboundPayload

ToolBackgroundWsMaterializer = Callable[
    [ToolOutputEvent], Awaitable[WsOutboundPayload]
]


class WebSocketDownlink:
    """Enqueue tool-background companion events as WS outbound payloads."""

    def __init__(
        self,
        outbound_queue: asyncio.Queue[WsOutboundPayload],
        tool_background_materializer: ToolBackgroundWsMaterializer,
    ) -> None:
        assert outbound_queue is not None
        assert tool_background_materializer is not None
        self._outbound_queue = outbound_queue
        self._tool_background_materializer = tool_background_materializer

    async def deliver(self, event: Downlink) -> None:
        """Materialize tool-background output when user-visible and enqueue for the WS pump."""
        if not downlink_delivers_user_visible_text(event):
            return
        match event.kind:
            case DownlinkKind.TOOL_BACKGROUND:
                await self._deliver_tool_background(event)
            case _:
                # TODO(companion-ws-bootstrap-downlink): BOOTSTRAP_INTERIM materializer. #3209 #3398
                # TODO(companion-ws-inner-tick-downlink): USER_REPLY / PROACTIVE / SCHEDULED / MAINTENANCE. #3210
                raise NotImplementedError(
                    f"WebSocketDownlink does not handle {event.kind}; "
                    "use bootstrap consumer or inner_tick_fire for this path"
                )

    async def _deliver_tool_background(self, event: Downlink) -> None:
        tool_output = event.tool_output
        assert tool_output is not None
        payload = await self._tool_background_materializer(tool_output)
        await self._outbound_queue.put(payload)
