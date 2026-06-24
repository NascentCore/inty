"""Weixin channel adapter stub (interface only; production bridge unchanged).

TODO(companion-channel-tools): No Weixin rename API — channel tools stay guidance-only
  (see weixin_clawbot_contact_alias_system_message); do not expose failing meta tools — #3362
TODO(weixin-reply-reaction): Quote/reply threading + emoji reactions via Hermes when iLink
  allows; align with ``WeixinDownlink`` — #3442 (epic #3440)
"""

from __future__ import annotations

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agent_channel.gateway import (
    GatewayKind,
)
from app.services.agentic_companion.downlink import ChannelDownlink
from app.services.agentic_companion.inner_tick_delivery import InnerTickDelivery


class _NoOpDownlink:
    async def deliver(self, event: object) -> None:
        return None


class WeixinChannelAdapterStub:
    """Stub adapter documenting ``channel_address=peer_id``, ``channel_user_id=wxid``."""

    @property
    def channel(self) -> GatewayKind:
        return GatewayKind.WECHAT_WEIXIN

    def as_downlink(self) -> ChannelDownlink:
        return _NoOpDownlink()

    async def on_turn_up(self, scope: AgentScope) -> None:
        assert scope is not None

    async def on_turn_down(self, scope: AgentScope) -> None:
        assert scope is not None

    def inner_tick_delivery(self) -> InnerTickDelivery:
        raise NotImplementedError(
            "WeixinChannelAdapterStub has no inner-tick delivery"
        )
