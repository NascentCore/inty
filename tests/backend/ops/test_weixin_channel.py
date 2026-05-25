"""Unit tests for Ops Weixin channel adapter wire parsing and routing."""

from __future__ import annotations

import pytest

from app.schemas.chat_websocket import ChatWsCompanionWireMessageMetaData
from backend.ops.weixin_channel.inty_ws_client import (
    _assistant_text_from_response_payload,
    http_base_to_ws_chat_url,
    is_proactive_chat_downlink,
)
from backend.ops.weixin_channel.session import (
    WeixinChannelBinding,
    WeixinChannelSession,
)


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
