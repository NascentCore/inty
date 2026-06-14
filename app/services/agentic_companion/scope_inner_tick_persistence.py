"""Postgres scope discovery for the scope inner-tick worker (persistency boundary)."""

from __future__ import annotations

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.companion_scope_listing import (
    list_companion_memory_scopes,
)
from app.db.session import AsyncSessionLocal

# TODO(scope-listing-due-filter): Narrow to scopes due for dreaming/maintenance — #3423.


async def fetch_initialized_companion_scopes() -> list[CompanionScope]:
    """Return distinct scopes with initialized ``context_json`` in Postgres."""
    async with AsyncSessionLocal() as db:
        return await list_companion_memory_scopes(db)
