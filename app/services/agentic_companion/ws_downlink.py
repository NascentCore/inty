"""WebSocket downlink adapter: ``Downlink`` → outbound queue."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from app.core.companion_harness.tools.tool_background import ToolOutputEvent
from app.services.agentic_companion.downlink import (
    Downlink,
    DownlinkKind,
    downlink_delivers_user_visible_text,
)
from app.services.agentic_companion.ws_deliver_ctx import WsDownlinkDeliverCtx
from app.services.ws_session_messages import WsOutboundPayload

ToolBackgroundWsMaterializer = Callable[
    [ToolOutputEvent], Awaitable[WsOutboundPayload]
]
BootstrapInterimWsMaterializer = Callable[
    [Downlink, WsDownlinkDeliverCtx], Awaitable[None]
]
LoopForegroundWsMaterializer = Callable[
    [Downlink, WsDownlinkDeliverCtx], Awaitable[None]
]


class WebSocketDownlink:
    """Enqueue companion downlink events as WS outbound payloads."""

    def __init__(
        self,
        outbound_queue: asyncio.Queue[WsOutboundPayload],
        tool_background_materializer: ToolBackgroundWsMaterializer,
        *,
        bootstrap_interim_materializer: BootstrapInterimWsMaterializer | None,
        loop_foreground_materializer: LoopForegroundWsMaterializer | None,
        deliver_ctx: WsDownlinkDeliverCtx | None,
    ) -> None:
        assert outbound_queue is not None
        assert tool_background_materializer is not None
        self._outbound_queue = outbound_queue
        self._tool_background_materializer = tool_background_materializer
        self._bootstrap_interim_materializer = bootstrap_interim_materializer
        self._loop_foreground_materializer = loop_foreground_materializer
        self._deliver_ctx = deliver_ctx

    def bind_deliver_ctx(self, ctx: WsDownlinkDeliverCtx | None) -> None:
        """Set per-turn context for bootstrap interim materialization."""
        self._deliver_ctx = ctx

    async def deliver(self, event: Downlink) -> None:
        """Materialize user-visible downlink and enqueue for the WS pump."""
        if not downlink_delivers_user_visible_text(event):
            return
        match event.kind:
            case DownlinkKind.TOOL_BACKGROUND:
                await self._deliver_tool_background(event)
            case DownlinkKind.BOOTSTRAP_INTERIM:
                await self._deliver_bootstrap_interim(event)
            case DownlinkKind.USER_REPLY:
                await self._deliver_loop_foreground(event)
            case _:
                raise NotImplementedError(
                    f"WebSocketDownlink does not handle {event.kind}"
                )

    async def _deliver_tool_background(self, event: Downlink) -> None:
        tool_output = event.tool_output
        assert tool_output is not None
        payload = await self._tool_background_materializer(tool_output)
        await self._outbound_queue.put(payload)

    async def _deliver_bootstrap_interim(self, event: Downlink) -> None:
        assert event.bootstrap_interim is not None
        ctx = self._deliver_ctx
        materializer = self._bootstrap_interim_materializer
        if ctx is None or materializer is None:
            return
        await materializer(event, ctx)

    async def _deliver_loop_foreground(self, event: Downlink) -> None:
        """Settled DUAL_LLM per-call foreground stream (terminal turn frame uses chat_ws)."""
        ctx = self._deliver_ctx
        materializer = self._loop_foreground_materializer
        if ctx is None or materializer is None:
            return
        await materializer(event, ctx)
