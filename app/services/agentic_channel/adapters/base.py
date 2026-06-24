"""Channel adapter protocol for agent-channel stack.

TODO(rename-channel-to-gateway): Rename ``ChannelAdapter`` → ``Gateway`` (Protocol); each — #3548
implementation declares ``gateway_kind: ChannelKind`` from ``agent_channel/channel_kind.py``.
Adapters must not define the canonical enum.
TODO(companion-channel-tools): Extend protocol with channel tool execution hooks (or sibling
  port) so harness dispatch stays out of transport details — #3362
TODO(channel-inbound-outbound-affordances): Add inbound envelope + outbound reply/reaction hooks
  to ``ChannelAdapter`` — epic #3440; Telegram #3441; Weixin #3442
"""

from __future__ import annotations

from typing import Protocol

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agent_channel.channel_kind import (
    ChannelKind,
)
from app.services.agentic_companion.downlink import ChannelDownlink
from app.services.agentic_companion.inner_tick_delivery import InnerTickDelivery


class ChannelAdapter(Protocol):
    """Transport-specific hooks for one ``CompanionRuntimeChannel``."""

    @property
    def channel(self) -> ChannelKind: ...

    def as_downlink(self) -> ChannelDownlink:
        """Return downlink used while this channel is ACTIVE."""

    async def on_turn_up(self, scope: AgentScope) -> None: ...

    async def on_turn_down(self, scope: AgentScope) -> None: ...

    def inner_tick_delivery(self) -> InnerTickDelivery:
        """Return proactive/scheduled delivery sink while this channel is ACTIVE."""
