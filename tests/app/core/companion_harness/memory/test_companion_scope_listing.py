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
    MemoryStoreScopePaths,
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


def test_scope_listing_context_compaction_state_json_kind_matches_accessor() -> None:
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.context_compaction_state_json
    kind, calendar_date = parse_memory_store_relative_path(rel)
    assert kind == CompanionMemoryDocumentKind.COMPANION_CONTEXT_COMPACTION_STATE_JSON
    assert calendar_date is None


def test_scope_listing_schedule_tasks_json_kind_matches_accessor() -> None:
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.schedule_queue_json
    kind, calendar_date = parse_memory_store_relative_path(rel)
    assert kind == CompanionMemoryDocumentKind.COMPANION_SCHEDULE_TASKS_JSON
    assert calendar_date is None


def test_scope_listing_memory_daily_raw_kind_matches_accessor() -> None:
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.memory_daily_gist("2026-09-15")
    kind, calendar_date = parse_memory_store_relative_path(rel)
    assert kind == CompanionMemoryDocumentKind.MEMORY_DAILY_RAW
    assert calendar_date is not None
    assert calendar_date.isoformat() == "2026-09-15"


def test_scope_listing_inty_v2_dreaming_state_json_kind_matches_accessor() -> None:
    paths = MemoryStoreScopePaths(state_file_prefix=".inty_v2")
    rel = paths.dreaming_state_json
    kind, calendar_date = parse_memory_store_relative_path(rel)
    assert kind == CompanionMemoryDocumentKind.INTY_V2_DREAMING_STATE_JSON
    assert calendar_date is None


def test_scope_listing_inty_v2_schedule_tasks_json_kind_matches_accessor() -> None:
    paths = MemoryStoreScopePaths(state_file_prefix=".inty_v2")
    rel = paths.schedule_queue_json
    kind, calendar_date = parse_memory_store_relative_path(rel)
    assert kind == CompanionMemoryDocumentKind.INTY_V2_SCHEDULE_TASKS_JSON
    assert calendar_date is None
