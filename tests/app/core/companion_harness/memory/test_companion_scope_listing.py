"""Tests for Postgres companion scope listing (#3255)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.companion_scope_listing import (
    list_companion_memory_scopes,
)
from app.core.companion_harness.memory.memory_store_document_mapping import (
    CompanionMemoryDocumentKind,
    parse_memory_store_relative_path,
)
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)


@pytest.mark.asyncio
async def test_list_companion_memory_scopes_distinct_triples() -> None:
    db = MagicMock()
    result = MagicMock()
    result.all.return_value = [
        ("user-1", "agent-1", "chat-1"),
        ("user-2", "agent-2", "chat-2"),
        ("", "agent-3", "chat-3"),
    ]
    db.execute = AsyncMock(return_value=result)

    scopes = await list_companion_memory_scopes(db)

    assert scopes == [
        CompanionScope("user-1", "agent-1", "chat-1"),
        CompanionScope("user-2", "agent-2", "chat-2"),
    ]


def test_scope_listing_context_json_kind_matches_accessor() -> None:
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.context_json
    kind, calendar_date = parse_memory_store_relative_path(rel)
    assert kind == CompanionMemoryDocumentKind.CONTEXT_JSON
    assert calendar_date is None
