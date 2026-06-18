"""Guest user + agent provisioning for agent-channel onboard (no legacy chat row).

Identity for companion / telegram-demo / weixin paths uses ``User.id`` and ``Agent.id``
only. Do **not** read or write legacy ``readable_id`` here (maintenance-mode HTTP APIs
may still touch it). Enforced by ``chat_ws_boundary.companion_surface_readable_id_references``.

TODO(telegram-dedicated-bot-bonding): Triage portal to provision per-user bot token and
  bind 1 user : 1 bot : 1 agent — #3361 (epic #3395; Option A constraints #3396)

TODO(cross-channel-consistent-identity): #3491 — route this onboard path through
  canonical channel identity resolution before provisioning.
"""

from __future__ import annotations

from dataclasses import dataclass

from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.core.model_selection import select_chat_model
from app.db.session import AsyncSessionLocal
from app.models.agent import Agent
from app.models.user import User
from app.core.companion_harness.agent_channel.guest_agent_kind import (
    companion_guest_agent_kind_for_channel,
)
from app.services.agentic_channel.companion_bonds import (
    require_active_companion_bond,
)
from app.services.agentic_channel.companion_guest_provision import (
    ProvisionGuestScopeInput,
    provision_guest_scope,
)
from app.services.agentic_channel.endpoints import (
    assert_inbound_endpoint_identity,
    resolve_scope,
    resolve_scope_by_channel_user_id,
    upsert_endpoint_in_session,
)
from app.services.agentic_channel.errors import (
    ChannelEndpointConflictError,
    integrity_error_detail,
)
from app.services.agentic_channel.turn import ensure_memory_store_session
from app.services.global_services import subscription_service


@dataclass(frozen=True)
class ChannelProvisionResult:
    scope: AgentScope
    is_new_user: bool
    channel_address: str
    channel_user_id: str


async def _require_active_bond_for_scope(scope: AgentScope) -> None:
    async with AsyncSessionLocal() as db:
        await require_active_companion_bond(db, scope)


async def _provision_result_after_bind_race(
    *,
    channel: CompanionRuntimeChannel,
    channel_address: str,
    channel_user_id: str,
) -> ChannelProvisionResult:
    """Return existing scope when a concurrent transaction won the endpoint insert."""
    raced = await resolve_scope(
        channel=channel, channel_address=channel_address
    )
    if raced is None:
        raced = await resolve_scope_by_channel_user_id(
            channel=channel, channel_user_id=channel_user_id
        )
    if raced is None:
        logger.error(
            "agent_channel onboard race recovery failed channel={} channel_address={} channel_user_id={}",
            channel.value,
            channel_address,
            channel_user_id,
        )
        raise ChannelEndpointConflictError(
            "endpoint bind violates unique constraint"
        )
    logger.info(
        "agent_channel onboard race recovery ok channel={} channel_address={} channel_user_id={} user_id={} agent_id={}",
        channel.value,
        channel_address,
        channel_user_id,
        raced.user_id,
        raced.agent_id,
    )
    await assert_inbound_endpoint_identity(
        channel=channel,
        channel_address=channel_address,
        channel_user_id=channel_user_id,
    )
    await _require_active_bond_for_scope(raced)
    await ensure_memory_store_session(raced)
    return ChannelProvisionResult(
        scope=raced,
        is_new_user=False,
        channel_address=channel_address,
        channel_user_id=channel_user_id,
    )


async def provision_agent_for_channel_onboard(
    *,
    channel: CompanionRuntimeChannel,
    channel_address: str,
    channel_user_id: str,
) -> ChannelProvisionResult:
    """Idempotent onboard: resolve existing endpoint or create guest user + agent."""
    assert channel_address != ""
    assert channel_user_id != ""

    by_address = await resolve_scope(
        channel=channel, channel_address=channel_address
    )
    by_user = await resolve_scope_by_channel_user_id(
        channel=channel, channel_user_id=channel_user_id
    )
    if by_address is not None or by_user is not None:
        await assert_inbound_endpoint_identity(
            channel=channel,
            channel_address=channel_address,
            channel_user_id=channel_user_id,
        )
    if by_address is not None and by_user is not None:
        if by_address.registry_key() != by_user.registry_key():
            logger.warning(
                "agent_channel onboard scope split channel={} channel_address={} channel_user_id={} by_address={} by_user={}",
                channel.value,
                channel_address,
                channel_user_id,
                by_address.registry_key(),
                by_user.registry_key(),
            )
            raise ChannelEndpointConflictError(
                "channel_address and channel_user_id resolve to different scopes"
            )
        logger.info(
            "agent_channel onboard existing scope channel={} channel_address={} channel_user_id={} user_id={} agent_id={}",
            channel.value,
            channel_address,
            channel_user_id,
            by_address.user_id,
            by_address.agent_id,
        )
        await _require_active_bond_for_scope(by_address)
        return ChannelProvisionResult(
            scope=by_address,
            is_new_user=False,
            channel_address=channel_address,
            channel_user_id=channel_user_id,
        )
    if by_address is not None:
        logger.info(
            "agent_channel onboard existing by_address channel={} channel_address={} channel_user_id={} user_id={} agent_id={}",
            channel.value,
            channel_address,
            channel_user_id,
            by_address.user_id,
            by_address.agent_id,
        )
        await _require_active_bond_for_scope(by_address)
        return ChannelProvisionResult(
            scope=by_address,
            is_new_user=False,
            channel_address=channel_address,
            channel_user_id=channel_user_id,
        )
    if by_user is not None:
        logger.info(
            "agent_channel onboard existing by_user channel={} channel_address={} channel_user_id={} user_id={} agent_id={}",
            channel.value,
            channel_address,
            channel_user_id,
            by_user.user_id,
            by_user.agent_id,
        )
        await _require_active_bond_for_scope(by_user)
        return ChannelProvisionResult(
            scope=by_user,
            is_new_user=False,
            channel_address=channel_address,
            channel_user_id=channel_user_id,
        )

    async with AsyncSessionLocal() as db:
        pending_user_id = ""
        pending_agent_id = ""
        try:
            scope = await provision_guest_scope(
                db,
                ProvisionGuestScopeInput(
                    kind=companion_guest_agent_kind_for_channel(channel),
                    nickname_prefix="Guest",
                    meta_data={"agent_channel": True},
                ),
            )
            pending_user_id = scope.user_id
            pending_agent_id = scope.agent_id
            await upsert_endpoint_in_session(
                db,
                scope,
                channel=channel,
                channel_address=channel_address,
                channel_user_id=channel_user_id,
            )
            await db.commit()
        except ChannelEndpointConflictError as exc:
            logger.warning(
                "agent_channel onboard bind conflict channel={} channel_address={} channel_user_id={} user_id={} agent_id={} error={}",
                channel.value,
                channel_address,
                channel_user_id,
                pending_user_id,
                pending_agent_id,
                exc,
            )
            await db.rollback()
            return await _provision_result_after_bind_race(
                channel=channel,
                channel_address=channel_address,
                channel_user_id=channel_user_id,
            )
        except IntegrityError as exc:
            logger.warning(
                "agent_channel onboard integrity error channel={} channel_address={} channel_user_id={} user_id={} agent_id={} {}",
                channel.value,
                channel_address,
                channel_user_id,
                pending_user_id,
                pending_agent_id,
                integrity_error_detail(exc),
            )
            await db.rollback()
            return await _provision_result_after_bind_race(
                channel=channel,
                channel_address=channel_address,
                channel_user_id=channel_user_id,
            )

    logger.info(
        "agent_channel onboard created channel={} channel_address={} channel_user_id={} user_id={} agent_id={}",
        channel.value,
        channel_address,
        channel_user_id,
        scope.user_id,
        scope.agent_id,
    )
    await ensure_memory_store_session(scope)
    return ChannelProvisionResult(
        scope=scope,
        is_new_user=True,
        channel_address=channel_address,
        channel_user_id=channel_user_id,
    )


async def provision_agent_for_existing_agent(
    *,
    channel: CompanionRuntimeChannel,
    channel_address: str,
    channel_user_id: str,
    agent_id: str,
) -> ChannelProvisionResult:
    """Bind channel endpoint to an existing companion agent (tests only; not wired in transport).

    The existing agent must already have an active companion bond.
    """
    assert channel_address != ""
    assert channel_user_id != ""
    assert agent_id != ""

    existing = await resolve_scope(
        channel=channel, channel_address=channel_address
    )
    if existing is not None:
        await assert_inbound_endpoint_identity(
            channel=channel,
            channel_address=channel_address,
            channel_user_id=channel_user_id,
        )
        await _require_active_bond_for_scope(existing)
        return ChannelProvisionResult(
            scope=existing,
            is_new_user=False,
            channel_address=channel_address,
            channel_user_id=channel_user_id,
        )

    async with AsyncSessionLocal() as db:
        agent_row = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = agent_row.scalar_one_or_none()
        if agent is None:
            raise ValueError(f"companion agent not found: {agent_id}")
        scope = AgentScope(user_id=agent.creator_id, agent_id=agent_id)
        await require_active_companion_bond(db, scope)

        pending_user_id = scope.user_id
        pending_agent_id = scope.agent_id
        try:
            await upsert_endpoint_in_session(
                db,
                scope,
                channel=channel,
                channel_address=channel_address,
                channel_user_id=channel_user_id,
            )
            await db.commit()
        except ChannelEndpointConflictError as exc:
            logger.warning(
                "agent_channel bind existing agent conflict channel={} channel_address={} channel_user_id={} agent_id={} user_id={} error={}",
                channel.value,
                channel_address,
                channel_user_id,
                agent_id,
                pending_user_id,
                exc,
            )
            await db.rollback()
            return await _provision_result_after_bind_race(
                channel=channel,
                channel_address=channel_address,
                channel_user_id=channel_user_id,
            )
        except IntegrityError as exc:
            logger.warning(
                "agent_channel bind existing agent integrity error channel={} channel_address={} channel_user_id={} agent_id={} user_id={} {}",
                channel.value,
                channel_address,
                channel_user_id,
                agent_id,
                pending_user_id,
                integrity_error_detail(exc),
            )
            await db.rollback()
            return await _provision_result_after_bind_race(
                channel=channel,
                channel_address=channel_address,
                channel_user_id=channel_user_id,
            )

    await ensure_memory_store_session(scope)
    return ChannelProvisionResult(
        scope=scope,
        is_new_user=False,
        channel_address=channel_address,
        channel_user_id=channel_user_id,
    )


async def resolve_chat_model_for_scope(scope: AgentScope):
    """Select chat model for a guest scope (subscription-aware)."""
    async with AsyncSessionLocal() as db:
        user_row = await db.execute(
            select(User).where(User.id == scope.user_id)
        )
        user = user_row.scalar_one_or_none()
        if user is None:
            raise ValueError(f"user not found: {scope.user_id}")
        subscription = await subscription_service.get_user_current_subscription(
            db, scope.user_id
        )
        return select_chat_model(
            user=user,
            is_subscribed=bool(subscription),
        )
