"""Guest user + agent provisioning for agent-channel onboard (no legacy chat row)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.core.model_selection import select_chat_model
from app.core.uuid import get_new_user_id
from app.db.session import AsyncSessionLocal
from app.models.agent import Agent, AgentVisibility
from app.models.user import AuthType, User
from app.schemas.agent import AgentCreate
from app.services import agent_service
from app.services.agentic_channel.endpoints import (
    assert_inbound_endpoint_identity,
    bind_endpoint,
    resolve_scope,
    resolve_scope_by_channel_user_id,
)
from app.services.agentic_channel.errors import ChannelEndpointConflictError
from app.services.agentic_channel.turn import ensure_memory_store_session
from app.services.global_services import subscription_service
from app.services.user_service import generate_next_readable_id


@dataclass(frozen=True)
class ChannelProvisionResult:
    scope: AgentScope
    is_new_user: bool
    channel_address: str
    channel_user_id: str


def _default_agent_create(*, tag: str) -> AgentCreate:
    return AgentCreate(
        name=f"agent-channel-{tag}",
        gender="FEMALE",
        visibility=AgentVisibility.PRIVATE,
        intro="Agent channel companion.",
        opening="Hello.",
        personality="Warm, curious.",
        scenario="Multi-channel companion.",
    )


async def _create_guest_user(db: AsyncSession) -> User:
    user_id = get_new_user_id()
    readable_id = await generate_next_readable_id(db)
    suffix = user_id[-8:]
    user = User(
        id=user_id,
        readable_id=readable_id,
        auth_type=AuthType.GUEST,
        nickname=f"Guest_{suffix}",
        meta_data={"agent_channel": True},
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _first_private_agent_for_user(
    db: AsyncSession,
    user_id: str,
) -> Agent | None:
    assert user_id != ""
    stmt = (
        select(Agent)
        .where(
            Agent.creator_id == user_id,
            Agent.visibility == AgentVisibility.PRIVATE,
        )
        .order_by(Agent.created_at.asc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


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
            raise ChannelEndpointConflictError(
                "channel_address and channel_user_id resolve to different scopes"
            )
        return ChannelProvisionResult(
            scope=by_address,
            is_new_user=False,
            channel_address=channel_address,
            channel_user_id=channel_user_id,
        )
    if by_address is not None:
        return ChannelProvisionResult(
            scope=by_address,
            is_new_user=False,
            channel_address=channel_address,
            channel_user_id=channel_user_id,
        )
    if by_user is not None:
        return ChannelProvisionResult(
            scope=by_user,
            is_new_user=False,
            channel_address=channel_address,
            channel_user_id=channel_user_id,
        )

    async with AsyncSessionLocal() as db:
        user = await _create_guest_user(db)
        is_new_user = True
        tag = uuid.uuid4().hex[:10]
        agent = await agent_service.create_agent(
            db,
            agent_in=_default_agent_create(tag=tag),
            user_id=user.id,
        )
        scope = AgentScope(user_id=user.id, agent_id=agent.id)

    await bind_endpoint(
        scope,
        channel=channel,
        channel_address=channel_address,
        channel_user_id=channel_user_id,
    )
    await ensure_memory_store_session(scope)
    return ChannelProvisionResult(
        scope=scope,
        is_new_user=is_new_user,
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
    """Bind channel endpoint to an existing companion agent (tests only; not wired in transport)."""
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

        user = await _create_guest_user(db)
        scope = AgentScope(user_id=user.id, agent_id=agent_id)

    await bind_endpoint(
        scope,
        channel=channel,
        channel_address=channel_address,
        channel_user_id=channel_user_id,
    )
    await ensure_memory_store_session(scope)
    return ChannelProvisionResult(
        scope=scope,
        is_new_user=True,
        channel_address=channel_address,
        channel_user_id=channel_user_id,
    )


async def resolve_chat_model_for_scope(scope: AgentScope):
    """Select chat model for a guest scope (subscription-aware)."""
    async with AsyncSessionLocal() as db:
        user_row = await db.execute(select(User).where(User.id == scope.user_id))
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
