"""List companion MemoryStore scopes from Postgres (process-wide discovery for #3255)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store_document_mapping import (
    CompanionMemoryDocumentKind,
)
from app.models.companion_memory_documents import CompanionMemoryDocumentVersion

# TODO(scope-listing-due-filter): Narrow to scopes due for dreaming/monolog — #3423.


async def list_companion_memory_scopes(
    db: AsyncSession,
) -> list[CompanionScope]:
    """Return distinct initialized scopes (rows with ``context_json`` document kind)."""
    result = await db.execute(
        select(
            CompanionMemoryDocumentVersion.user_id,
            CompanionMemoryDocumentVersion.companion_id,
            CompanionMemoryDocumentVersion.chat_id,
        )
        .where(
            CompanionMemoryDocumentVersion.document_kind
            == CompanionMemoryDocumentKind.CONTEXT_JSON.value
        )
        .distinct()
    )
    scopes: list[CompanionScope] = []
    for user_id, companion_id, chat_id in result.all():
        uid = str(user_id or "").strip()
        aid = str(companion_id or "").strip()
        cid = str(chat_id or "").strip()
        if not uid or not aid or not cid:
            continue
        scopes.append(
            CompanionScope(
                user_id=uid,
                companion_id=aid,
                chat_id=cid,
            )
        )
    return scopes
