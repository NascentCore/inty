"""Tests for companion runtime gateway classification."""

from __future__ import annotations

from app.core.companion_harness.agent_channel.gateway import (
    GatewayKind,
    is_im_gateway,
)


def test_is_im_gateway_weixin_and_telegram() -> None:
    assert is_im_gateway(GatewayKind.WECHAT_WEIXIN) is True
    assert is_im_gateway(GatewayKind.TELEGRAM) is True


def test_is_im_gateway_app_and_sms() -> None:
    assert is_im_gateway(GatewayKind.APP_WS) is False
    assert is_im_gateway(GatewayKind.SMS) is False
