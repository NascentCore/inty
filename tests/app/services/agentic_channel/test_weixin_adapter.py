"""Weixin channel adapter stub tests."""

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.services.agentic_channel.adapters.weixin import WeixinChannelAdapterStub


def test_weixin_stub_channel_and_lifecycle() -> None:
    adapter = WeixinChannelAdapterStub()
    assert adapter.channel == CompanionRuntimeChannel.WECHAT_WEIXIN
    scope = AgentScope(user_id="u", agent_id="a")
    assert adapter.as_downlink() is not None
