"""Tests for queue-centric WebSocket outbound pump."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import WebSocketDisconnect

from app.services.chat_websocket_session import chat_ws_outbound_pump
from app.services.ws_session_messages import WsOutboundPayload


@pytest.mark.asyncio
async def test_chat_ws_outbound_pump_fifo_order() -> None:
    sent: list[WsOutboundPayload] = []
    ws = AsyncMock()
    ws.send_json = AsyncMock(side_effect=lambda p: sent.append(dict(p)))

    q: asyncio.Queue[WsOutboundPayload] = asyncio.Queue()
    pump = asyncio.create_task(chat_ws_outbound_pump(ws, q))
    await q.put({"code": 200, "seq": 1})
    await q.put({"code": 200, "seq": 2})
    await asyncio.sleep(0)
    pump.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pump
    assert sent == [{"code": 200, "seq": 1}, {"code": 200, "seq": 2}]


@pytest.mark.asyncio
async def test_chat_ws_outbound_pump_send_json_disconnect_exits_cleanly() -> None:
    ws = AsyncMock()
    ws.send_json = AsyncMock(side_effect=WebSocketDisconnect())

    q: asyncio.Queue[WsOutboundPayload] = asyncio.Queue()
    pump = asyncio.create_task(chat_ws_outbound_pump(ws, q))
    await q.put({"code": 200, "payload": 1})
    await asyncio.sleep(0)
    assert pump.done()
    await pump
    assert ws.send_json.await_count == 1
