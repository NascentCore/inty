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


async def get_companion_bond_for_scope(
    db: AsyncSession,
    scope: AgentScope,
) -> CompanionBond | None:
    """Return the exact bond row for scope, or None when not unique."""
    assert scope.user_id != ""
    assert scope.agent_id != ""
    result = await db.execute(
        select(CompanionBond)
        .where(
            CompanionBond.user_id == scope.user_id,
            CompanionBond.agent_id == scope.agent_id,
        )
        .order_by(CompanionBond.created_at.asc(), CompanionBond.id.asc())
    )
    bonds = list(result.scalars().all())
    if len(bonds) != 1:
        return None
    return bonds[0]


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
    """Return valid, unambiguous keys for ACTIVE bonds with running runtime."""
    result = await db.execute(
        select(CompanionBond)
        .where(
            CompanionBond.state == CompanionBondState.ACTIVE,
            CompanionBond.runtime_paused_at.is_(None),
        )
        .order_by(CompanionBond.created_at.asc(), CompanionBond.id.asc())
    )
    bonds = list(result.scalars().all())
    user_counts: dict[str, int] = {}
    agent_counts: dict[str, int] = {}
    for bond in bonds:
        user_counts[bond.user_id] = user_counts.get(bond.user_id, 0) + 1
        agent_counts[bond.agent_id] = agent_counts.get(bond.agent_id, 0) + 1

    keys: set[tuple[str, str]] = set()
    for bond in bonds:
        if user_counts[bond.user_id] != 1 or agent_counts[bond.agent_id] != 1:
            continue
        scope = _active_scope_from_single_bond(bond)
        try:
            await _require_live_scope_rows(db, scope)
        except CompanionBondInvariantError:
            continue
        keys.add((scope.user_id, scope.agent_id))
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


async def pause_companion_bond_runtime(
    db: AsyncSession,
    scope: AgentScope,
) -> bool:
    """Mark one ACTIVE bond runtime paused; return whether the flag was set."""
    bond = await require_active_companion_bond(db, scope)
    if bond.runtime_paused_at is not None:
        return False
    bond.runtime_paused_at = datetime.now(UTC)
    return True


async def resume_companion_bond_runtime(
    db: AsyncSession,
    scope: AgentScope,
) -> bool:
    """Clear runtime pause flag for one ACTIVE bond; return whether it changed."""
    bond = await require_active_companion_bond(db, scope)
    if bond.runtime_paused_at is None:
        return False
    bond.runtime_paused_at = None
    bond.last_resumed_at = datetime.now(UTC)
    return True


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
