"""Queue-centric helpers for ``/api/v1/chat/ws`` (inty-ws message-io pump)."""

from __future__ import annotations

import asyncio

from fastapi import WebSocket
from loguru import logger

from app.services.ws_session_messages import WsOutboundPayload


async def chat_ws_outbound_pump(
    websocket: WebSocket,
    outbound_queue: asyncio.Queue[WsOutboundPayload],
) -> None:
    """FIFO drain of outbound JSON payloads produced by adapters/handlers onto the WebSocket."""
    try:
        while True:
            payload = await outbound_queue.get()
            try:
                await websocket.send_json(payload)
            except Exception:
                logger.exception("chat_ws_outbound_pump send_json failed")
                raise
    except asyncio.CancelledError:
        raise
