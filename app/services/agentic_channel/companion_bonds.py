"""Service-level invariants for active companion bonds."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.models.agent import Agent
from app.models.companion_bond import CompanionBond, CompanionBondState
from app.models.user import User
from app.services.agentic_channel.errors import CompanionBondInvariantError


async def _active_bonds_for_scope_keys(
    db: AsyncSession,
    scope: AgentScope,
) -> list[CompanionBond]:
    assert scope.user_id != ""
    assert scope.agent_id != ""
    result = await db.execute(
        select(CompanionBond)
        .where(
            CompanionBond.state == CompanionBondState.ACTIVE,
            or_(
                CompanionBond.user_id == scope.user_id,
                CompanionBond.agent_id == scope.agent_id,
            ),
        )
        .order_by(CompanionBond.created_at.asc(), CompanionBond.id.asc())
    )
    return list(result.scalars().all())


def _active_scope_from_single_bond(bond: CompanionBond) -> AgentScope:
    return AgentScope(user_id=bond.user_id, agent_id=bond.agent_id)


async def _require_live_scope_rows(
    db: AsyncSession,
    scope: AgentScope,
) -> None:
    assert scope.user_id != ""
    assert scope.agent_id != ""
    user_row = await db.execute(
        select(User).where(
            User.id == scope.user_id,
            User.deleted_at.is_(None),
        )
    )
    if user_row.scalar_one_or_none() is None:
        raise CompanionBondInvariantError(
            f"active companion bond user missing or deleted: {scope.user_id}"
        )
    agent_row = await db.execute(
        select(Agent).where(
            Agent.id == scope.agent_id,
            Agent.deleted_at.is_(None),
        )
    )
    agent = agent_row.scalar_one_or_none()
    if agent is None:
        raise CompanionBondInvariantError(
            f"active companion bond agent missing or deleted: {scope.agent_id}"
        )
    if agent.creator_id != scope.user_id:
        raise CompanionBondInvariantError(
            "active companion bond agent creator does not match user"
        )


async def create_active_companion_bond(
    db: AsyncSession,
    scope: AgentScope,
) -> CompanionBond:
    """Create one ACTIVE user-companion bond after service-level uniqueness checks."""
    assert scope.user_id != ""
    assert scope.agent_id != ""
    await _require_live_scope_rows(db, scope)
    existing = await _active_bonds_for_scope_keys(db, scope)
    if existing:
        keys = ", ".join(
            _active_scope_from_single_bond(bond).registry_key()
            for bond in existing
        )
        raise CompanionBondInvariantError(
            f"active companion bond already exists for scope keys: {keys}"
        )
    bond = CompanionBond(
        id=str(uuid.uuid4()),
        user_id=scope.user_id,
        agent_id=scope.agent_id,
        state=CompanionBondState.ACTIVE,
    )
    db.add(bond)
    return bond


async def require_active_companion_bond(
    db: AsyncSession,
    scope: AgentScope,
) -> CompanionBond:
    """Require exactly one ACTIVE bond for scope and verify live user/agent rows."""
    assert scope.user_id != ""
    assert scope.agent_id != ""
    bonds = await _active_bonds_for_scope_keys(db, scope)
    exact = [
        bond
        for bond in bonds
        if bond.user_id == scope.user_id and bond.agent_id == scope.agent_id
    ]
    if len(bonds) != 1 or len(exact) != 1:
        keys = ", ".join(
            _active_scope_from_single_bond(bond).registry_key()
            for bond in bonds
        )
        raise CompanionBondInvariantError(
            "active companion bond missing, ambiguous, or mismatched for "
            f"{scope.registry_key()}: {keys}"
        )
    await _require_live_scope_rows(db, scope)
    return exact[0]


async def has_active_companion_bond_for_agent(
    db: AsyncSession,
    agent_id: str,
) -> bool:
    """Return whether agent_id has exactly one valid ACTIVE bond."""
    assert agent_id != ""
    result = await db.execute(
        select(CompanionBond).where(
            CompanionBond.agent_id == agent_id,
            CompanionBond.state == CompanionBondState.ACTIVE,
        )
    )
    bonds = list(result.scalars().all())
    if len(bonds) != 1:
        return False
    scope = _active_scope_from_single_bond(bonds[0])
    conflicts = await _active_bonds_for_scope_keys(db, scope)
    if len(conflicts) != 1:
        return False
    try:
        await _require_live_scope_rows(db, scope)
    except CompanionBondInvariantError:
        return False
    return True


async def has_active_companion_bond(
    db: AsyncSession,
    scope: AgentScope,
) -> bool:
    """Return whether scope has exactly one valid ACTIVE bond row."""
    assert scope.user_id != ""
    assert scope.agent_id != ""
    bonds = await _active_bonds_for_scope_keys(db, scope)
    exact = [
        bond
        for bond in bonds
        if bond.user_id == scope.user_id and bond.agent_id == scope.agent_id
    ]
    if len(bonds) != 1 or len(exact) != 1:
        return False
    try:
        await _require_live_scope_rows(db, scope)
    except CompanionBondInvariantError:
        return False
    return True


async def list_active_companion_agent_scope_keys(
    db: AsyncSession,
) -> frozenset[tuple[str, str]]:
    """Return (user_id, agent_id) keys for every ACTIVE companion bond."""
    result = await db.execute(
        select(CompanionBond.user_id, CompanionBond.agent_id).where(
            CompanionBond.state == CompanionBondState.ACTIVE,
        )
    )
    keys: set[tuple[str, str]] = set()
    for user_id, agent_id in result.all():
        uid = str(user_id or "").strip()
        aid = str(agent_id or "").strip()
        if uid and aid:
            keys.add((uid, aid))
    return frozenset(keys)


async def deactivate_companion_bond(
    db: AsyncSession,
    scope: AgentScope,
) -> CompanionBond:
    """Mark one ACTIVE bond INACTIVE (caller commits)."""
    bond = await require_active_companion_bond(db, scope)
    bond.state = CompanionBondState.INACTIVE
    bond.inactive_at = datetime.now(UTC)
    return bond


async def active_companion_scope_for_user(
    db: AsyncSession,
    user_id: str,
) -> AgentScope:
    """Return exactly one ACTIVE companion scope for user, or raise loudly."""
    assert user_id != ""
    result = await db.execute(
        select(CompanionBond)
        .where(
            CompanionBond.user_id == user_id,
            CompanionBond.state == CompanionBondState.ACTIVE,
        )
        .order_by(CompanionBond.created_at.asc(), CompanionBond.id.asc())
    )
    bonds = list(result.scalars().all())
    if len(bonds) != 1:
        keys = ", ".join(
            _active_scope_from_single_bond(bond).registry_key()
            for bond in bonds
        )
        raise CompanionBondInvariantError(
            f"expected one active companion bond for user {user_id}: {keys}"
        )
    scope = _active_scope_from_single_bond(bonds[0])
    await _require_live_scope_rows(db, scope)
    return scope
