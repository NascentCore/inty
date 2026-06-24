"""Provision Inty user, agent, and bridge JWT after Weixin iLink QR confirm.

Identity uses ``User.id`` and ``Agent.id`` only; legacy ``readable_id`` is unused.
Enforced by ``chat_ws_boundary.companion_surface_readable_id_references``.

TODO(cross-channel-consistent-identity): #3491 — replace iLink-local user lookup
  with canonical channel identity resolution before companion provisioning.
"""

from __future__ import annotations

from dataclasses import dataclass

from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agent_channel.channel_kind import (
    ChannelKind,
)
from app.core.security import create_access_token
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
    integrity_error_detail,
)

_WEIXIN_CHANNEL = ChannelKind.WECHAT_WEIXIN


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


async def _provision_result_after_bind_race(
    ilink_user_id: str,
) -> ProvisionResult:
    assert ilink_user_id != ""
    scope = await _resolve_existing_weixin_scope(ilink_user_id)
    if scope is None:
        raise ChannelEndpointConflictError(
            "weixin endpoint bind violates unique constraint"
        )
    await _require_active_weixin_scope(scope)
    jwt = create_access_token(scope.user_id)
    return ProvisionResult(
        user_id=scope.user_id,
        agent_id=scope.agent_id,
        jwt=jwt,
        is_new_user=False,
    )


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
        pending_user_id = ""
        pending_agent_id = ""
        stale_user = await _user_by_ilink_user_id(db, ilink_user_id)
        if stale_user is not None:
            raise CompanionBondInvariantError(
                "weixin iLink user exists without channel endpoint bond"
            )
        try:
            scope = await provision_guest_scope(
                db,
                ProvisionGuestScopeInput(channel=ChannelKind.WECHAT_WEIXIN,
                    nickname_prefix="Weixin",
                    meta_data={"ilink_user_id": ilink_user_id},
                ),
            )
            pending_user_id = scope.user_id
            pending_agent_id = scope.agent_id
            await upsert_endpoint_in_session(
                db,
                scope,
                channel=_WEIXIN_CHANNEL,
                channel_address=ilink_user_id,
                channel_user_id=ilink_user_id,
            )
            await db.commit()
        except ChannelEndpointConflictError as exc:
            logger.warning(
                "weixin onboard bind conflict ilink_user_id={} user_id={} agent_id={} error={}",
                ilink_user_id,
                pending_user_id,
                pending_agent_id,
                exc,
            )
            await db.rollback()
            return await _provision_result_after_bind_race(ilink_user_id)
        except IntegrityError as exc:
            logger.warning(
                "weixin onboard integrity error ilink_user_id={} user_id={} agent_id={} {}",
                ilink_user_id,
                pending_user_id,
                pending_agent_id,
                integrity_error_detail(exc),
            )
            await db.rollback()
            return await _provision_result_after_bind_race(ilink_user_id)
        user_id = scope.user_id
        agent_id = scope.agent_id

        jwt = create_access_token(user_id)
        return ProvisionResult(
            user_id=user_id,
            agent_id=agent_id,
            jwt=jwt,
            is_new_user=True,
        )
