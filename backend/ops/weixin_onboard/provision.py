"""Provision Inty user, agent, and bridge JWT after Weixin iLink QR confirm.

Identity uses ``User.id`` and ``Agent.id`` only; legacy ``readable_id`` is unused.
Enforced by ``chat_ws_boundary.companion_surface_readable_id_references``.

TODO(cross-channel-consistent-identity): #3491 — replace iLink-local user lookup
  with canonical channel identity resolution before companion provisioning.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.core.companion_harness.agent_channel.guest_agent_kind import (
    CompanionGuestAgentKind,
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
    CompanionBondInvariantError,
)

_WEIXIN_CHANNEL = CompanionRuntimeChannel.WECHAT_WEIXIN


@dataclass(frozen=True)
class ProvisionResult:
    """Inty credentials for Weixin bridge binding (JWT is Ops-internal only)."""

    user_id: str
    agent_id: str
    jwt: str
    is_new_user: bool


async def _user_by_ilink_user_id(
    db: AsyncSession,
    ilink_user_id: str,
) -> User | None:
    assert ilink_user_id != ""
    stmt = select(User).where(
        User.deleted_at.is_(None),
        User.meta_data["ilink_user_id"].as_string() == ilink_user_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _resolve_existing_weixin_scope(
    ilink_user_id: str,
) -> AgentScope | None:
    assert ilink_user_id != ""
    by_address = await resolve_scope(
        channel=_WEIXIN_CHANNEL,
        channel_address=ilink_user_id,
    )
    by_user = await resolve_scope_by_channel_user_id(
        channel=_WEIXIN_CHANNEL,
        channel_user_id=ilink_user_id,
    )
    if by_address is None and by_user is None:
        return None
    await assert_inbound_endpoint_identity(
        channel=_WEIXIN_CHANNEL,
        channel_address=ilink_user_id,
        channel_user_id=ilink_user_id,
    )
    if by_address is not None and by_user is not None:
        if by_address.registry_key() != by_user.registry_key():
            raise ChannelEndpointConflictError(
                "weixin channel address and user id resolve to different scopes"
            )
        return by_address
    if by_address is not None:
        return by_address
    return by_user


async def _require_active_weixin_scope(scope: AgentScope) -> None:
    async with AsyncSessionLocal() as db:
        await require_active_companion_bond(db, scope)


async def provision_inty_for_ilink_user(
    *, ilink_user_id: str
) -> ProvisionResult:
    """Get or create Inty user + PRIVATE agent; mint JWT for bridge binding."""
    assert ilink_user_id != ""
    existing_scope = await _resolve_existing_weixin_scope(ilink_user_id)
    if existing_scope is not None:
        await _require_active_weixin_scope(existing_scope)
        jwt = create_access_token(existing_scope.user_id)
        return ProvisionResult(
            user_id=existing_scope.user_id,
            agent_id=existing_scope.agent_id,
            jwt=jwt,
            is_new_user=False,
        )

    async with AsyncSessionLocal() as db:
        stale_user = await _user_by_ilink_user_id(db, ilink_user_id)
        if stale_user is not None:
            raise CompanionBondInvariantError(
                "weixin iLink user exists without channel endpoint bond"
            )
        scope = await provision_guest_scope(
            db,
            ProvisionGuestScopeInput(
                kind=CompanionGuestAgentKind.WEIXIN,
                nickname_prefix="Weixin",
                meta_data={"ilink_user_id": ilink_user_id},
            ),
        )
        await upsert_endpoint_in_session(
            db,
            scope,
            channel=_WEIXIN_CHANNEL,
            channel_address=ilink_user_id,
            channel_user_id=ilink_user_id,
        )
        await db.commit()
        user_id = scope.user_id
        agent_id = scope.agent_id

        jwt = create_access_token(user_id)
        return ProvisionResult(
            user_id=user_id,
            agent_id=agent_id,
            jwt=jwt,
            is_new_user=True,
        )
