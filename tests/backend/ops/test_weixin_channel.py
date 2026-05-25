"""Unit tests for Ops Weixin channel adapter wire parsing and routing."""

from __future__ import annotations

import asyncio
import json

import pytest
import websockets

from app.schemas.chat_websocket import ChatWsCompanionWireMessageMetaData, ChatWsPingFrame
from backend.ops.weixin_channel.inty_ws_client import (
    IntyWsChannelClient,
    IntyWsChannelConfig,
    _WS_PING_INTERVAL_SEC,
    _assistant_text_from_response_payload,
    http_base_to_ws_chat_url,
    is_proactive_chat_downlink,
)
from backend.ops.weixin_channel.session import (
    WeixinChannelBinding,
    WeixinChannelSession,
)


def test_ws_ping_interval_below_server_idle_minimum() -> None:
    assert _WS_PING_INTERVAL_SEC == 9.0
    assert _WS_PING_INTERVAL_SEC < 10.0


def test_ws_ping_frame_wire_json() -> None:
    payload = ChatWsPingFrame().model_dump_json()
    assert json.loads(payload) == {"type": "ping"}


@pytest.mark.asyncio
async def test_pinger_loop_emits_ping_on_interval() -> None:
    received: list[str] = []

    async def handler(ws: websockets.ServerConnection) -> None:
        async for raw in ws:
            received.append(str(raw))

    async with websockets.serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        async with websockets.connect(f"ws://127.0.0.1:{port}") as ws:
            client = IntyWsChannelClient(
                IntyWsChannelConfig(
                    api_base_url="http://127.0.0.1:8001",
                    jwt="jwt",
                    agent_id="agent-1",
                ),
                on_proactive_push=_noop_proactive_push,
                timezone_name=None,
            )
            client._ws = ws
            ping_task = asyncio.create_task(client._pinger_loop())
            try:
                await asyncio.sleep(_WS_PING_INTERVAL_SEC + 0.5)
            finally:
                ping_task.cancel()
                try:
                    await ping_task
                except asyncio.CancelledError:
                    pass

    ping_frames = [json.loads(raw) for raw in received]
    assert ping_frames == [{"type": "ping"}]


@pytest.mark.asyncio
async def test_pinger_loop_prevents_idle_disconnect() -> None:
    """Ping keepalive resets server idle timer (WeChat demo ConnectionClosedOK regression)."""
    idle_sec = 12.0

    async def handler(ws: websockets.ServerConnection) -> None:
        while True:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=idle_sec)
            except asyncio.TimeoutError:
                await ws.close()
                return
            data = json.loads(str(raw))
            if data.get("type") == "ping":
                await ws.send(json.dumps({"type": "pong"}))

    async with websockets.serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        async with websockets.connect(f"ws://127.0.0.1:{port}") as ws:
            client = IntyWsChannelClient(
                IntyWsChannelConfig(
                    api_base_url="http://127.0.0.1:8001",
                    jwt="jwt",
                    agent_id="agent-1",
                ),
                on_proactive_push=_noop_proactive_push,
                timezone_name=None,
            )
            client._ws = ws
            ping_task = asyncio.create_task(client._pinger_loop())
            try:
                # Without ping, server closes at ``idle_sec``; first ping at 9s keeps link up.
                await asyncio.sleep(idle_sec + 3.0)
                await ws.send(ChatWsPingFrame().model_dump_json())
                raw = await asyncio.wait_for(ws.recv(), timeout=idle_sec)
                assert json.loads(str(raw)) == {"type": "pong"}
            finally:
                ping_task.cancel()
                try:
                    await ping_task
                except asyncio.CancelledError:
                    pass


async def _noop_proactive_push(_text: str) -> None:
    return None


def test_http_base_to_ws_chat_url() -> None:
    url = http_base_to_ws_chat_url("http://127.0.0.1:8001", "conn-1")
    assert url.startswith("ws://127.0.0.1:8001/api/v1/chat/ws?")
    assert "ws_conn_id=conn-1" in url


def test_is_proactive_chat_downlink_companion_flag() -> None:
    meta = ChatWsCompanionWireMessageMetaData(companion_proactive_chat=True)
    assert is_proactive_chat_downlink(meta) is True


def test_is_proactive_chat_downlink_inner_tick_activity() -> None:
    meta = ChatWsCompanionWireMessageMetaData(
        inner_tick_activity="proactive_chat",
    )
    assert is_proactive_chat_downlink(meta) is True


def test_is_proactive_chat_downlink_normal_reply() -> None:
    meta = ChatWsCompanionWireMessageMetaData(source="companion")
    assert is_proactive_chat_downlink(meta) is False


def test_assistant_text_from_chat_ws_response() -> None:
    raw = {
        "code": 200,
        "message": "success",
        "data": {
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "hello"},
                    "finish_reason": "stop",
                }
            ],
        },
        "agent_id": "agent-1",
    }
    assert _assistant_text_from_response_payload(raw) == "hello"


@pytest.mark.asyncio
async def test_proactive_push_without_last_peer_id_is_dropped() -> None:
    binding = WeixinChannelBinding(
        user_id="user-1",
        agent_id="agent-1",
        inty_api_base_url="http://127.0.0.1:8001",
        inty_jwt="jwt",
        weixin_account_id="wx-acct",
        weixin_token="token",
        weixin_base_url="https://ilinkai.weixin.qq.com",
    )
    session = WeixinChannelSession(binding=binding)
    await session._handle_proactive_push("proactive text")


@pytest.mark.asyncio
async def test_proactive_push_with_last_peer_id_calls_transport() -> None:
    class _RecordingTransport:
        def __init__(self) -> None:
            self.sent: list[tuple[str, str]] = []

        async def send_text(self, peer_id: str, text: str) -> None:
            self.sent.append((peer_id, text))

    binding = WeixinChannelBinding(
        user_id="user-1",
        agent_id="agent-1",
        inty_api_base_url="http://127.0.0.1:8001",
        inty_jwt="jwt",
        weixin_account_id="wx-acct",
        weixin_token="token",
        weixin_base_url="https://ilinkai.weixin.qq.com",
        last_peer_id="peer-42",
    )
    session = WeixinChannelSession(binding=binding)
    transport = _RecordingTransport()
    session._transport = transport
    await session._handle_proactive_push("proactive hello")
    assert transport.sent == [("peer-42", "proactive hello")]
