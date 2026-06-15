"""Unit tests for Ops Weixin channel adapter wire parsing and routing."""

from __future__ import annotations

import json

import pytest

from app.schemas.chat_websocket import ChatWsPingFrame
from backend.ops.weixin_channel.session import (
    WeixinChannelBinding,
    WeixinChannelSession,
    weixin_bridge_reply_for_inbound,
)


async def _noop_ilink_session_expired() -> None:
    pass
from backend.ops.weixin_channel.transport import WeixinInboundMessage
from app.utils.config import WeixinChannelConfig


def test_weixin_channel_config_split_multiline_default_false() -> None:
    cfg = WeixinChannelConfig()
    assert cfg.split_multiline_messages is False


def test_weixin_channel_config_split_multiline_true_from_yaml_dict() -> None:
    cfg = WeixinChannelConfig.model_validate(
        {"split_multiline_messages": True},
    )
    assert cfg.split_multiline_messages is True


def test_weixin_adapter_split_multiline_reads_platform_extra() -> None:
    """Hermes reads PlatformConfig.extra; transport injects split_multiline_messages."""
    from gateway.config import PlatformConfig
    from gateway.platforms.weixin import WeixinAdapter

    base_extra = {
        "account_id": "wx-acct",
        "base_url": "https://ilinkai.weixin.qq.com",
        "dm_policy": "open",
        "group_policy": "disabled",
    }
    adapter_false = WeixinAdapter(
        PlatformConfig(
            enabled=True,
            token="test-token",
            extra={**base_extra, "split_multiline_messages": False},
        ),
    )
    adapter_true = WeixinAdapter(
        PlatformConfig(
            enabled=True,
            token="test-token",
            extra={**base_extra, "split_multiline_messages": True},
        ),
    )
    assert adapter_false._split_multiline_messages is False
    assert adapter_true._split_multiline_messages is True

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
    class _RecordingTransport:
        def __init__(self) -> None:
            self.sent: list[tuple[str, str]] = []

        async def send_text(self, peer_id: str, text: str) -> None:
            self.sent.append((peer_id, text))

    transport = _RecordingTransport()
    session._transport = transport
    presence = _RecordingPresence()
    session._presence = presence
    inbound = WeixinInboundMessage(
        account_id="wx-acct",
        peer_id="peer-42",
        text="",
        media_paths=("/tmp/weixin-voice.silk",),
        media_types=("audio/silk",),
    )
    await session._handle_inbound(inbound)
    assert presence.calls == []
    assert transport.sent
    assert "voice" in transport.sent[0][1].lower()


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
    class _RecordingTransport:
        def __init__(self) -> None:
            self.sent: list[tuple[str, str]] = []

        async def send_text(self, peer_id: str, text: str) -> None:
            self.sent.append((peer_id, text))

    transport = _RecordingTransport()
    session._transport = transport
    presence = _RecordingPresence()
    session._presence = presence
    inbound = WeixinInboundMessage(
        account_id="wx-acct",
        peer_id="peer-42",
        text="",
        media_paths=("/tmp/weixin-image.jpg",),
        media_types=("image/jpeg",),
    )
    await session._handle_inbound(inbound)
    assert presence.calls == []
    assert transport.sent
    assert "image" in transport.sent[0][1].lower()


@pytest.mark.asyncio
async def test_handle_inbound_text_forwards_to_inprocess_presence() -> None:
    class _RecordingPresence:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def handle_user_text(self, user_text: str) -> str:
            self.calls.append(user_text)
            return ""

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
    class _RecordingTransport:
        def __init__(self) -> None:
            self.sent: list[tuple[str, str]] = []

        async def send_text(self, peer_id: str, text: str) -> None:
            self.sent.append((peer_id, text))

    transport = _RecordingTransport()
    session._transport = transport
    presence = _RecordingPresence()
    session._presence = presence
    inbound = WeixinInboundMessage(
        account_id="wx-acct",
        peer_id="peer-42",
        text="  hello  ",
        media_paths=(),
        media_types=(),
    )
    await session._handle_inbound(inbound)
    assert presence.calls == ["hello"]
    assert transport.sent == []
