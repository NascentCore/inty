"""Tests for queue-centric WebSocket outbound pump."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi import WebSocketDisconnect

from app.schemas.chat_websocket import ChatWebSocketQueuedSuccessFrame
from app.services.chat_completion_wire import build_chat_ws_queued_success_frame
from app.services.chat_websocket_session import chat_ws_outbound_pump
from app.services.ws_session_messages import WsOutboundPayload
from tests.app.schemas.test_chat_websocket_completion_models import (
    FOREGROUND_CHAT_META,
    _base_completion_data,
)
from app.schemas.chat_websocket import ChatWsCompletionData


def _sample_success_frame() -> ChatWebSocketQueuedSuccessFrame:
    completion = ChatWsCompletionData.model_validate(
        _base_completion_data(FOREGROUND_CHAT_META)
    )
    return build_chat_ws_queued_success_frame(
        completion=completion,
        agent_id="agent-uuid",
        status_line="Online",
    )


@pytest.mark.asyncio
async def test_chat_ws_outbound_pump_fifo_order() -> None:
    sent: list[dict[str, object]] = []
    ws = AsyncMock()
    ws.send_json = AsyncMock(side_effect=lambda p: sent.append(dict(p)))

    q: asyncio.Queue[WsOutboundPayload] = asyncio.Queue()
    pump = asyncio.create_task(chat_ws_outbound_pump(ws, q))
    frame1 = _sample_success_frame()
    frame2 = _sample_success_frame()
    await q.put(frame1)
    await q.put(frame2)
    await asyncio.sleep(0)
    pump.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pump
    assert sent == [
        frame1.model_dump(exclude_none=True),
        frame2.model_dump(exclude_none=True),
    ]


@pytest.mark.asyncio
async def test_chat_ws_outbound_pump_send_json_disconnect_exits_cleanly() -> (
    None
):
    ws = AsyncMock()
    ws.send_json = AsyncMock(side_effect=WebSocketDisconnect())

    q: asyncio.Queue[WsOutboundPayload] = asyncio.Queue()
    pump = asyncio.create_task(chat_ws_outbound_pump(ws, q))
    await q.put(_sample_success_frame())
    await asyncio.sleep(0)
    assert pump.done()
    await pump
    assert ws.send_json.await_count == 1
