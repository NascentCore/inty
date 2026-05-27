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
    IntyWsChannelState,
    _WS_PING_INTERVAL_SEC,
    _assistant_text_from_response_payload,
    http_base_to_ws_chat_url,
    is_proactive_chat_downlink,
)
from backend.ops.weixin_channel.session import (
    WeixinChannelBinding,
    WeixinChannelSession,
    weixin_bridge_reply_for_inbound,
)
from backend.ops.weixin_channel.transport import WeixinInboundMessage


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


@pytest.mark.asyncio
async def test_send_user_text_reconnects_after_normal_close() -> None:
    """A stale WeChat bridge WS should reconnect before surfacing Hermes /reset copy."""
    connection_count = 0

    async def handler(ws: websockets.ServerConnection) -> None:
        nonlocal connection_count
        connection_count += 1
        await ws.recv()
        await ws.send(json.dumps({"type": "client_context_ack", "ok": True}))
        await ws.recv()
        await ws.send(json.dumps({"type": "user_signed_on_ack", "ok": True}))
        if connection_count == 1:
            await ws.close()
            return
        await ws.recv()
        await ws.send(
            json.dumps(
                {
                    "code": 200,
                    "message": "success",
                    "data": {
                        "choices": [
                            {
                                "index": 0,
                                "message": {
                                    "role": "assistant",
                                    "content": "after reconnect",
                                },
                                "finish_reason": "stop",
                            }
                        ],
                    },
                    "agent_id": "agent-1",
                }
            )
        )

    async with websockets.serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        client = IntyWsChannelClient(
            IntyWsChannelConfig(
                api_base_url=f"http://127.0.0.1:{port}",
                jwt="jwt",
                agent_id="agent-1",
            ),
            on_proactive_push=_noop_proactive_push,
            timezone_name=None,
        )
        await client.connect()
        try:
            deadline = asyncio.get_running_loop().time() + 3.0
            while client.state != IntyWsChannelState.FAILED:
                if asyncio.get_running_loop().time() > deadline:
                    raise AssertionError("client did not observe server close")
                await asyncio.sleep(0.01)
            assert await client.send_user_text("hello") == "after reconnect"
        finally:
            await client.disconnect()

    assert connection_count == 2


async def _noop_proactive_push(_text: str) -> None:
    return None


def test_weixin_bridge_reply_for_image_only_inbound() -> None:
    reply = weixin_bridge_reply_for_inbound(
        text="",
        media_types=("image/jpeg",),
    )
    assert reply is not None
    assert "text" in reply.lower()
    assert "image" in reply.lower()


def test_weixin_bridge_reply_for_empty_non_image_inbound() -> None:
    reply = weixin_bridge_reply_for_inbound(text="  ", media_types=())
    assert reply is not None
    assert "text message" in reply.lower()


def test_weixin_bridge_reply_for_image_with_caption_forwards() -> None:
    reply = weixin_bridge_reply_for_inbound(
        text="what is this?",
        media_types=("image/jpeg",),
    )
    assert reply is None


def test_weixin_bridge_reply_for_plain_text_forwards() -> None:
    reply = weixin_bridge_reply_for_inbound(text="hello", media_types=())
    assert reply is None


@pytest.mark.asyncio
async def test_handle_inbound_image_only_does_not_call_inty_ws() -> None:
    class _RecordingWsClient:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def send_user_text(self, user_text: str) -> str:
            self.calls.append(user_text)
            return "should not be used"

    binding = WeixinChannelBinding(
        user_id="user-1",
        agent_id="agent-1",
        inty_api_base_url="http://127.0.0.1:8001",
        inty_jwt="jwt",
        weixin_account_id="wx-acct",
        weixin_token="token",
        weixin_base_url="https://ilinkai.weixin.qq.com",
    )
    session = WeixinChannelSession(binding=binding, on_binding_peer_updated=None)
    ws_client = _RecordingWsClient()
    session._ws_client = ws_client
    inbound = WeixinInboundMessage(
        account_id="wx-acct",
        peer_id="peer-42",
        text="",
        media_paths=("/tmp/weixin-image.jpg",),
        media_types=("image/jpeg",),
    )
    reply = await session._handle_inbound(inbound)
    assert ws_client.calls == []
    assert reply is not None
    assert "image" in reply.lower()


@pytest.mark.asyncio
async def test_handle_inbound_text_forwards_to_inty_ws() -> None:
    class _RecordingWsClient:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def send_user_text(self, user_text: str) -> str:
            self.calls.append(user_text)
            return "companion reply"

    binding = WeixinChannelBinding(
        user_id="user-1",
        agent_id="agent-1",
        inty_api_base_url="http://127.0.0.1:8001",
        inty_jwt="jwt",
        weixin_account_id="wx-acct",
        weixin_token="token",
        weixin_base_url="https://ilinkai.weixin.qq.com",
    )
    session = WeixinChannelSession(binding=binding, on_binding_peer_updated=None)
    ws_client = _RecordingWsClient()
    session._ws_client = ws_client
    inbound = WeixinInboundMessage(
        account_id="wx-acct",
        peer_id="peer-42",
        text="  hello  ",
        media_paths=(),
        media_types=(),
    )
    reply = await session._handle_inbound(inbound)
    assert ws_client.calls == ["hello"]
    assert reply == "companion reply"

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
    session = WeixinChannelSession(binding=binding, on_binding_peer_updated=None)
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
    session = WeixinChannelSession(binding=binding, on_binding_peer_updated=None)
    transport = _RecordingTransport()
    session._transport = transport
    await session._handle_proactive_push("proactive hello")
    assert transport.sent == [("peer-42", "proactive hello")]
