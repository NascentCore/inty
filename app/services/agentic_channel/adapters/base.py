"""Channel adapter protocol for agent-channel stack."""

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
