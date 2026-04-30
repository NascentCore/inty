"""Tests for queue-centric WebSocket outbound pump."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

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
async def test_repl_pop_downlink_maps_bridge_tuple() -> None:
    from tools.inty_v2_repl.repl_message_io import pop_downlink_item

    bridge = MagicMock()
    bridge.try_pop_queued_chat.return_value = ("hello", None, {"source": "chat"})
    item = pop_downlink_item(bridge)
    assert item is not None
    assert item["kind"] == "assistant"
    assert item["text"] == "hello"

    bridge.try_pop_queued_chat.return_value = (None, (400, "bad"), {})
    err_item = pop_downlink_item(bridge)
    assert err_item is not None
    assert err_item["kind"] == "ws_error"
    assert err_item["code"] == 400
