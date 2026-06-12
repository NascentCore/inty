"""Postgres persistence for agent-channel endpoints."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.db.session import AsyncSessionLocal
from app.models.agent_channel_endpoint import AgentChannelEndpoint
from app.services.agentic_channel.errors import ChannelEndpointConflictError


class EndpointRecord(BaseModel):
    """One bonded channel endpoint row."""

    model_config = ConfigDict(frozen=True)

    user_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    channel: CompanionRuntimeChannel
    channel_address: str = Field(min_length=1)
    channel_user_id: str = Field(min_length=1)

    def to_scope(self) -> AgentScope:
        return AgentScope(user_id=self.user_id, agent_id=self.agent_id)


def _row_to_record(row: AgentChannelEndpoint) -> EndpointRecord:
    return EndpointRecord(
        user_id=row.user_id,
        agent_id=row.agent_id,
        channel=CompanionRuntimeChannel(row.channel),
        channel_address=row.channel_address,
        channel_user_id=row.channel_user_id,
    )


async def _find_by_address(
    db: AsyncSession,
    *,
    channel: CompanionRuntimeChannel,
    channel_address: str,
) -> AgentChannelEndpoint | None:
    result = await db.execute(
        select(AgentChannelEndpoint).where(
            AgentChannelEndpoint.channel == channel.value,
            AgentChannelEndpoint.channel_address == channel_address,
        )
    )
    return result.scalar_one_or_none()


async def _find_by_channel_user_id(
    db: AsyncSession,
    *,
    channel: CompanionRuntimeChannel,
    channel_user_id: str,
) -> AgentChannelEndpoint | None:
    result = await db.execute(
        select(AgentChannelEndpoint).where(
            AgentChannelEndpoint.channel == channel.value,
            AgentChannelEndpoint.channel_user_id == channel_user_id,
        )
    )
    return result.scalar_one_or_none()


async def _find_by_agent_channel(
    db: AsyncSession,
    *,
    agent_id: str,
    channel: CompanionRuntimeChannel,
) -> AgentChannelEndpoint | None:
    result = await db.execute(
        select(AgentChannelEndpoint).where(
            AgentChannelEndpoint.agent_id == agent_id,
            AgentChannelEndpoint.channel == channel.value,
        )
    )
    return result.scalar_one_or_none()


def _assert_bind_compatible(
    *,
    scope: AgentScope,
    channel: CompanionRuntimeChannel,
    channel_address: str,
    channel_user_id: str,
    by_address: AgentChannelEndpoint | None,
    by_user: AgentChannelEndpoint | None,
    by_agent: AgentChannelEndpoint | None,
) -> None:
    if by_user is not None and by_user.user_id != scope.user_id:
        raise ChannelEndpointConflictError(
            f"channel_user_id already bound to another Inty user on {channel.value}"
        )
    if by_address is not None:
        if by_address.user_id != scope.user_id or by_address.agent_id != scope.agent_id:
            raise ChannelEndpointConflictError(
                f"channel_address already bound to another scope on {channel.value}"
            )
    if by_agent is not None:
        if by_agent.user_id != scope.user_id or by_agent.agent_id != scope.agent_id:
            raise ChannelEndpointConflictError(
                f"agent already has a different endpoint on {channel.value}"
            )
        if (
            by_agent.channel_address != channel_address
            or by_agent.channel_user_id != channel_user_id
        ):
            raise ChannelEndpointConflictError(
                f"agent endpoint mismatch on {channel.value}"
            )


async def upsert_endpoint_in_session(
    db: AsyncSession,
    scope: AgentScope,
    *,
    channel: CompanionRuntimeChannel,
    channel_address: str,
    channel_user_id: str,
) -> AgentChannelEndpoint:
    """Upsert endpoint row in ``db`` without committing."""
    assert scope.user_id != ""
    assert scope.agent_id != ""
    assert channel_address != ""
    assert channel_user_id != ""

    by_address = await _find_by_address(
        db, channel=channel, channel_address=channel_address
    )
    by_user = await _find_by_channel_user_id(
        db, channel=channel, channel_user_id=channel_user_id
    )
    by_agent = await _find_by_agent_channel(
        db, agent_id=scope.agent_id, channel=channel
    )
    _assert_bind_compatible(
        scope=scope,
        channel=channel,
        channel_address=channel_address,
        channel_user_id=channel_user_id,
        by_address=by_address,
        by_user=by_user,
        by_agent=by_agent,
    )

    row = by_agent or by_address or by_user
    if row is None:
        row = AgentChannelEndpoint(
            id=str(uuid.uuid4()),
            user_id=scope.user_id,
            agent_id=scope.agent_id,
            channel=channel.value,
            channel_address=channel_address,
            channel_user_id=channel_user_id,
        )
        db.add(row)
    else:
        row.user_id = scope.user_id
        row.agent_id = scope.agent_id
        row.channel_address = channel_address
        row.channel_user_id = channel_user_id
    return row


async def bind_endpoint(
    scope: AgentScope,
    *,
    channel: CompanionRuntimeChannel,
    channel_address: str,
    channel_user_id: str,
) -> EndpointRecord:
    """Upsert endpoint for ``scope``; enforce channel human ↔ Inty user 1:1."""
    async with AsyncSessionLocal() as db:
        row = await upsert_endpoint_in_session(
            db,
            scope,
            channel=channel,
            channel_address=channel_address,
            channel_user_id=channel_user_id,
        )
        try:
            await db.commit()
            await db.refresh(row)
        except IntegrityError as exc:
            await db.rollback()
            raise ChannelEndpointConflictError(
                "endpoint bind violates unique constraint"
            ) from exc
        return _row_to_record(row)


async def resolve_scope(
    *,
    channel: CompanionRuntimeChannel,
    channel_address: str,
) -> AgentScope | None:
    """Inbound routing: ``channel_address`` → ``AgentScope``."""
    assert channel_address != ""
    async with AsyncSessionLocal() as db:
        row = await _find_by_address(
            db, channel=channel, channel_address=channel_address
        )
        if row is None:
            return None
        return AgentScope(user_id=row.user_id, agent_id=row.agent_id)


async def resolve_scope_by_channel_user_id(
    *,
    channel: CompanionRuntimeChannel,
    channel_user_id: str,
) -> AgentScope | None:
    """Resolve scope by channel-side human id."""
    assert channel_user_id != ""
    async with AsyncSessionLocal() as db:
        row = await _find_by_channel_user_id(
            db, channel=channel, channel_user_id=channel_user_id
        )
        if row is None:
            return None
        return AgentScope(user_id=row.user_id, agent_id=row.agent_id)


async def get_endpoint_for_scope(
    scope: AgentScope,
    *,
    channel: CompanionRuntimeChannel,
) -> EndpointRecord | None:
    async with AsyncSessionLocal() as db:
        row = await _find_by_agent_channel(
            db, agent_id=scope.agent_id, channel=channel
        )
        if row is None or row.user_id != scope.user_id:
            return None
        return _row_to_record(row)


async def list_endpoints_for_agent(*, agent_id: str) -> list[EndpointRecord]:
    assert agent_id != ""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AgentChannelEndpoint)
            .where(AgentChannelEndpoint.agent_id == agent_id)
            .order_by(AgentChannelEndpoint.channel)
        )
        return [_row_to_record(row) for row in result.scalars().all()]


async def list_endpoints_for_channel(
    *,
    channel: CompanionRuntimeChannel,
) -> list[EndpointRecord]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AgentChannelEndpoint)
            .where(AgentChannelEndpoint.channel == channel.value)
            .order_by(AgentChannelEndpoint.channel_address)
        )
        return [_row_to_record(row) for row in result.scalars().all()]


async def inbound_channel_user_id_matches(
    *,
    channel: CompanionRuntimeChannel,
    channel_address: str,
    channel_user_id: str,
) -> bool:
    """Return whether inbound ``channel_user_id`` matches bonded endpoint row."""
    assert channel_address != ""
    assert channel_user_id != ""
    async with AsyncSessionLocal() as db:
        row = await _find_by_address(
            db, channel=channel, channel_address=channel_address
        )
        if row is None:
            return True
        return row.channel_user_id == channel_user_id


async def assert_inbound_endpoint_identity(
    *,
    channel: CompanionRuntimeChannel,
    channel_address: str,
    channel_user_id: str,
) -> None:
    """Raise when inbound address/user_id disagrees with a bonded endpoint row."""
    assert channel_address != ""
    assert channel_user_id != ""
    async with AsyncSessionLocal() as db:
        by_address = await _find_by_address(
            db, channel=channel, channel_address=channel_address
        )
        if (
            by_address is not None
            and by_address.channel_user_id != channel_user_id
        ):
            raise ChannelEndpointConflictError(
                "channel_user_id does not match endpoint bonded to channel_address"
            )
        by_user = await _find_by_channel_user_id(
            db, channel=channel, channel_user_id=channel_user_id
        )
        if by_user is not None and by_user.channel_address != channel_address:
            raise ChannelEndpointConflictError(
                "channel_address does not match endpoint bonded to channel_user_id"
            )
