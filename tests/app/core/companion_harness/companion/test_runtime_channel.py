"""Tests for companion runtime channel classification."""

from __future__ import annotations

from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
    is_im_runtime_channel,
)


def test_is_im_runtime_channel_weixin_and_telegram() -> None:
    assert is_im_runtime_channel(CompanionRuntimeChannel.WECHAT_WEIXIN) is True
    assert is_im_runtime_channel(CompanionRuntimeChannel.TELEGRAM) is True


def test_is_im_runtime_channel_app() -> None:
    assert is_im_runtime_channel(CompanionRuntimeChannel.APP) is False
