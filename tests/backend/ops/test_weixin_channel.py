"""Unit tests for Ops Weixin channel adapter wire parsing and routing."""

from __future__ import annotations

import json

import pytest

from app.schemas.chat_websocket import ChatWsCompanionWireMessageMetaData, ChatWsPingFrame
from backend.ops.weixin_channel.chat_ws_wire import (
    CHAT_WS_CLIENT_PING_INTERVAL_SEC,
    assistant_text_from_response_payload,
    http_base_to_ws_chat_url,
    is_proactive_chat_downlink,
)
from backend.ops.weixin_channel.session import (
    WeixinChannelBinding,
    WeixinChannelSession,
    weixin_bridge_reply_for_inbound,
)


async def _noop_ilink_session_expired() -> None:
    pass
from backend.ops.weixin_channel.transport import WeixinInboundMessage


def test_ws_ping_interval_below_server_idle_minimum() -> None:
    assert CHAT_WS_CLIENT_PING_INTERVAL_SEC == 9.0
    assert CHAT_WS_CLIENT_PING_INTERVAL_SEC < 10.0


def test_ws_ping_frame_wire_json() -> None:
    payload = ChatWsPingFrame().model_dump_json()
    assert json.loads(payload) == {"type": "ping"}


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


def test_weixin_bridge_reply_for_voice_only_inbound() -> None:
    reply = weixin_bridge_reply_for_inbound(
        text="",
        media_types=("audio/silk",),
    )
    assert reply is not None
    assert "voice" in reply.lower()


def test_weixin_bridge_reply_for_voice_transcription_forwards() -> None:
    reply = weixin_bridge_reply_for_inbound(
        text="hello there",
        media_types=(),
    )
    assert reply is None


@pytest.mark.asyncio
async def test_handle_inbound_voice_only_does_not_call_companion() -> None:
    class _RecordingPresence:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def handle_user_text(self, user_text: str) -> str:
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
    session = WeixinChannelSession(
        binding=binding,
        on_binding_peer_updated=None,
        on_ilink_session_expired=_noop_ilink_session_expired,
    )
    presence = _RecordingPresence()
    session._presence = presence
    inbound = WeixinInboundMessage(
        account_id="wx-acct",
        peer_id="peer-42",
        text="",
        media_paths=("/tmp/weixin-voice.silk",),
        media_types=("audio/silk",),
    )
    reply = await session._handle_inbound(inbound)
    assert presence.calls == []
    assert reply is not None
    assert "voice" in reply.lower()


@pytest.mark.asyncio
async def test_handle_inbound_image_only_does_not_call_companion() -> None:
    class _RecordingPresence:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def handle_user_text(self, user_text: str) -> str:
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
    session = WeixinChannelSession(
        binding=binding,
        on_binding_peer_updated=None,
        on_ilink_session_expired=_noop_ilink_session_expired,
    )
    presence = _RecordingPresence()
    session._presence = presence
    inbound = WeixinInboundMessage(
        account_id="wx-acct",
        peer_id="peer-42",
        text="",
        media_paths=("/tmp/weixin-image.jpg",),
        media_types=("image/jpeg",),
    )
    reply = await session._handle_inbound(inbound)
    assert presence.calls == []
    assert reply is not None
    assert "image" in reply.lower()


@pytest.mark.asyncio
async def test_handle_inbound_text_forwards_to_inprocess_presence() -> None:
    class _RecordingPresence:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def handle_user_text(self, user_text: str) -> str:
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
    session = WeixinChannelSession(
        binding=binding,
        on_binding_peer_updated=None,
        on_ilink_session_expired=_noop_ilink_session_expired,
    )
    presence = _RecordingPresence()
    session._presence = presence
    inbound = WeixinInboundMessage(
        account_id="wx-acct",
        peer_id="peer-42",
        text="  hello  ",
        media_paths=(),
        media_types=(),
    )
    reply = await session._handle_inbound(inbound)
    assert presence.calls == ["hello"]
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
    assert assistant_text_from_response_payload(raw) == "hello"
