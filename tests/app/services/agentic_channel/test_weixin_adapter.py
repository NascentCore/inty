"""Weixin channel adapter stub tests."""

from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
)
from app.services.agentic_channel.adapters.weixin import (
    WeixinChannelAdapterStub,
)


def test_weixin_stub_channel_and_lifecycle() -> None:
    adapter = WeixinChannelAdapterStub()
    assert adapter.channel == ChannelKind.WECHAT_WEIXIN
    assert adapter.as_downlink() is not None
