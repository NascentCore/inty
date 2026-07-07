"""Queue-centric helpers for ``/api/v1/chat/ws`` (inty-ws message-io pump).

Only **business / assistant** JSON goes through this FIFO to ``send_json``. Wire-level control
frames (ping/pong, client_context_ack) bypass the queue and are sent directly by the route; see
``chat._handle_chat_websocket_control_json``. If the client disconnects, ``send_json`` may raise
``WebSocketDisconnect``; the pump exits the drain loop without re-raising so teardown does not
treat a normal drop as an application error.
"""

from __future__ import annotations

import asyncio

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from app.services.ws_session_messages import WsOutboundPayload


async def chat_ws_outbound_pump(
    websocket: WebSocket,
    outbound_queue: asyncio.Queue[WsOutboundPayload],
) -> None:
    """FIFO drain of outbound JSON payloads produced by adapters/handlers onto the WebSocket."""
    try:
        while True:
            frame = await outbound_queue.get()
            try:
                await websocket.send_json(frame.model_dump(exclude_none=True))
            except WebSocketDisconnect:
                logger.debug(
                    "chat_ws_outbound_pump send_json: client disconnected"
                )
                break
            except Exception:
                logger.exception("chat_ws_outbound_pump send_json failed")
                raise
    except asyncio.CancelledError:
        raise
