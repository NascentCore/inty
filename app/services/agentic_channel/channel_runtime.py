"""Per-scope channel runtime state: bonded endpoints vs ACTIVE downlink."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from loguru import logger

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.services.agentic_channel.adapters.base import ChannelAdapter
from app.services.agentic_channel.endpoints import get_endpoint_for_scope
from app.services.agentic_companion.downlink import ChannelDownlink


class ChannelRuntimeState(StrEnum):
    INACTIVE = "inactive"
    ACTIVE = "active"


@dataclass
class ScopeChannelRegistry:
    """Process-local runtime state for one ``AgentScope``."""

    scope: AgentScope
    states: dict[CompanionRuntimeChannel, ChannelRuntimeState] = field(
        default_factory=dict
    )
    downlinks: dict[CompanionRuntimeChannel, ChannelDownlink] = field(
        default_factory=dict
    )
    adapters: dict[CompanionRuntimeChannel, ChannelAdapter] = field(
        default_factory=dict
    )

    def active_channel(self) -> CompanionRuntimeChannel | None:
        for channel, state in self.states.items():
            if state == ChannelRuntimeState.ACTIVE:
                return channel
        return None

    def state_of(self, channel: CompanionRuntimeChannel) -> ChannelRuntimeState:
        return self.states.get(channel, ChannelRuntimeState.INACTIVE)


_registries: dict[str, ScopeChannelRegistry] = {}


def get_scope_channel_registry(scope: AgentScope) -> ScopeChannelRegistry:
    key = scope.registry_key()
    existing = _registries.get(key)
    if existing is not None:
        return existing
    registry = ScopeChannelRegistry(scope=scope)
    _registries[key] = registry
    return registry


def clear_registries_for_tests() -> None:
    _registries.clear()


async def turn_channel_up(
    scope: AgentScope,
    channel: CompanionRuntimeChannel,
    *,
    adapter: ChannelAdapter,
    reason: str,
) -> None:
    """Make ``channel`` the sole ACTIVE channel for ``scope``."""
    assert reason != ""
    endpoint = await get_endpoint_for_scope(scope, channel=channel)
    if endpoint is None:
        raise ValueError(
            f"no endpoint row for scope={scope.registry_key()} channel={channel.value}"
        )

    registry = get_scope_channel_registry(scope)
    prior = registry.active_channel()
    if prior is not None and prior != channel:
        await turn_channel_down(scope, prior, reason="superseded")

    registry.states[channel] = ChannelRuntimeState.ACTIVE
    registry.adapters[channel] = adapter
    registry.downlinks[channel] = adapter.as_downlink()
    await adapter.on_turn_up(scope)
    logger.info(
        "agent_channel turn_up scope={} channel={} reason={}",
        scope.registry_key(),
        channel.value,
        reason,
    )


async def turn_channel_down(
    scope: AgentScope,
    channel: CompanionRuntimeChannel,
    *,
    reason: str,
) -> None:
    """Mark ``channel`` INACTIVE and drop its downlink."""
    assert reason != ""
    registry = get_scope_channel_registry(scope)
    if registry.state_of(channel) != ChannelRuntimeState.ACTIVE:
        return
    registry.states[channel] = ChannelRuntimeState.INACTIVE
    registry.downlinks.pop(channel, None)
    adapter = registry.adapters.pop(channel, None)
    if adapter is not None:
        await adapter.on_turn_down(scope)
    logger.info(
        "agent_channel turn_down scope={} channel={} reason={}",
        scope.registry_key(),
        channel.value,
        reason,
    )

