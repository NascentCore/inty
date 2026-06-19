"""Process-local runtime teardown when a companion bond is no longer ACTIVE."""

from __future__ import annotations

from loguru import logger

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.db.session import AsyncSessionLocal
from app.services.agentic_channel.channel_runtime import (
    ChannelRuntimeState,
    get_scope_channel_registry,
    turn_channel_down,
)
from app.services.agentic_channel.companion_bonds import (
    deactivate_companion_bond,
)
from app.services.agentic_channel.presence import stop_presence


async def turn_down_companion_agent_runtime(
    scope: AgentScope,
    *,
    reason: str,
) -> None:
    """Stop channel downlinks and presence for one companion scope."""
    assert reason != ""
    registry = get_scope_channel_registry(scope)
    for channel in list(registry.states.keys()):
        if registry.state_of(channel) == ChannelRuntimeState.ACTIVE:
            await turn_channel_down(scope, channel, reason=reason)
    await stop_presence(scope)
    logger.info(
        "companion_bond runtime turned down scope={} reason={}",
        scope.registry_key(),
        reason,
    )


async def deactivate_companion_bond_and_runtime(
    scope: AgentScope,
    *,
    reason: str,
) -> None:
    """Persist INACTIVE bond and tear down in-process companion runtime."""
    assert reason != ""
    async with AsyncSessionLocal() as db:
        await deactivate_companion_bond(db, scope)
        await db.commit()
    await turn_down_companion_agent_runtime(scope, reason=reason)
    logger.info(
        "companion_bond deactivated scope={} reason={}",
        scope.registry_key(),
        reason,
    )
