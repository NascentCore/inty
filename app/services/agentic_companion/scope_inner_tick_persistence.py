"""Postgres scope discovery for the scope inner-tick worker (persistency boundary)."""

from __future__ import annotations

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.companion_scope_listing import (
    list_companion_memory_scopes,
)
from app.db.session import AsyncSessionLocal
from app.services.agentic_channel.companion_bonds import (
    list_active_companion_agent_scope_keys,
)

# TODO(scope-listing-due-filter): Narrow to scopes due for dreaming/monolog — #3423.


async def fetch_initialized_companion_scopes() -> list[CompanionScope]:
    """Return initialized MemoryStore scopes whose companion bond is still ACTIVE."""
    async with AsyncSessionLocal() as db:
        memory_scopes = await list_companion_memory_scopes(db)
        active_keys = await list_active_companion_agent_scope_keys(db)
    return [
        scope
        for scope in memory_scopes
        if (scope.user_id, scope.companion_id) in active_keys
    ]
