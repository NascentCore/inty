"""Channel adapter protocol for agent-channel stack.

TODO(rename-channel-to-gateway): Rename ``ChannelAdapter`` to Gateway — adapters are gateways to
human channels (weixin/wechat, telegram, sms-phone-number, etc.).
TODO(companion-channel-tools): Extend protocol with channel tool execution hooks (or sibling
  port) so harness dispatch stays out of transport details — #3362
TODO(channel-inbound-outbound-affordances): Add inbound envelope + outbound reply/reaction hooks
  to ``ChannelAdapter`` — epic #3440; Telegram #3441; Weixin #3442
"""

from __future__ import annotations

from typing import Protocol

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.services.agentic_companion.downlink import ChannelDownlink


class ChannelAdapter(Protocol):
    """Transport-specific hooks for one ``CompanionRuntimeChannel``."""

    @property
    def channel(self) -> CompanionRuntimeChannel: ...

    def as_downlink(self) -> ChannelDownlink:
        """Return downlink used while this channel is ACTIVE."""

    async def on_turn_up(self, scope: AgentScope) -> None: ...

    async def on_turn_down(self, scope: AgentScope) -> None: ...
