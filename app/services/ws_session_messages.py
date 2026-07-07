"""Queue-centric WebSocket session types for ``/api/v1/chat/ws`` (inty-ws only).

Outbound queue items are typed Pydantic frames serialized at the pump boundary via
``model_dump(exclude_none=True)`` before ``WebSocket.send_json``.
"""

from __future__ import annotations

from typing import TypeAlias

from app.schemas.chat_websocket import (
    ChatWebSocketQueuedPlainError,
    ChatWebSocketQueuedSuccessFrame,
    ChatWsWsConnDroppedAckFrame,
)

WsOutboundFrame: TypeAlias = (
    ChatWebSocketQueuedSuccessFrame
    | ChatWebSocketQueuedPlainError
    | ChatWsWsConnDroppedAckFrame
)
WsOutboundPayload: TypeAlias = WsOutboundFrame
