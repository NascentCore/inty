"""Tests for companion runtime gateway classification."""

from __future__ import annotations

from app.core.companion_harness.agent_channel.channel_kind import (
    ChannelKind,
    is_im_channel,
)


def test_is_im_channel_weixin_and_telegram() -> None:
    assert is_im_channel(ChannelKind.WECHAT_WEIXIN) is True
    assert is_im_channel(ChannelKind.TELEGRAM) is True


def test_is_im_channel_app_and_sms() -> None:
    assert is_im_channel(ChannelKind.APP_WS) is False
    assert is_im_channel(ChannelKind.SMS) is False
