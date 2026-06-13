"""Weixin channel adapter stub (interface only; production bridge unchanged).

TODO(companion-channel-tools): No Weixin rename API — channel tools stay guidance-only
  (see weixin_clawbot_contact_alias_system_message); do not expose failing meta tools — #3362
"""

from __future__ import annotations

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.services.agentic_companion.downlink import ChannelDownlink


class _NoOpDownlink:
    async def deliver(self, event: object) -> None:
        return None


class WeixinChannelAdapterStub:
    """Stub adapter documenting ``channel_address=peer_id``, ``channel_user_id=wxid``."""

    @property
    def channel(self) -> CompanionRuntimeChannel:
        return CompanionRuntimeChannel.WECHAT_WEIXIN

    def as_downlink(self) -> ChannelDownlink:
        return _NoOpDownlink()

    async def on_turn_up(self, scope: AgentScope) -> None:
        assert scope is not None

    async def on_turn_down(self, scope: AgentScope) -> None:
        assert scope is not None
