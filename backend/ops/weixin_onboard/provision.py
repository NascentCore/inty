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

from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.core.companion_harness.agent_channel.guest_agent_kind import (
    CompanionGuestAgentKind,
)
from app.services.agentic_channel.companion_guest_provision import (
    ProvisionGuestScopeInput,
    add_companion_guest_agent_for_user,
    first_private_agent_for_user,
    provision_guest_scope,
)


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


async def provision_inty_for_ilink_user(
    *, ilink_user_id: str
) -> ProvisionResult:
    """Get or create Inty user + PRIVATE agent; mint JWT for bridge binding."""
    assert ilink_user_id != ""
    async with AsyncSessionLocal() as db:
        user = await _user_by_ilink_user_id(db, ilink_user_id)
        is_new_user = user is None
        if user is None:
            scope = await provision_guest_scope(
                db,
                ProvisionGuestScopeInput(
                    kind=CompanionGuestAgentKind.WEIXIN,
                    nickname_prefix="Weixin",
                    meta_data={"ilink_user_id": ilink_user_id},
                ),
            )
            await db.commit()
            user_id = scope.user_id
            agent_id = scope.agent_id
        else:
            # iLink may persist guest user before agent row exists (partial retry path).
            # Telegram/agent-channel onboard always creates user+agent atomically via
            # ``provision_guest_scope`` — no orphan-user recovery there.
            agent = await first_private_agent_for_user(db, user.id)
            if agent is None:
                agent = await add_companion_guest_agent_for_user(
                    db,
                    user_id=user.id,
                    kind=CompanionGuestAgentKind.WEIXIN,
                )
                await db.commit()
                await db.refresh(agent)
            user_id = user.id
            agent_id = agent.id

        jwt = create_access_token(user_id)
        return ProvisionResult(
            user_id=user_id,
            agent_id=agent_id,
            jwt=jwt,
            is_new_user=is_new_user,
        )
