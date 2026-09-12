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


def test_scope_listing_companion_user_feedback_jsonl_kind_matches_accessor() -> None:
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.companion_user_feedback_jsonl
    kind, calendar_date = parse_memory_store_relative_path(rel)
    assert kind == CompanionMemoryDocumentKind.COMPANION_USER_FEEDBACK_JSONL
    assert calendar_date is None


def test_scope_listing_significance_perception_kind_matches_accessor() -> None:
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.significance_perception_md
    kind, calendar_date = parse_memory_store_relative_path(rel)
    assert kind == CompanionMemoryDocumentKind.SIGNIFICANCE_PERCEPTION
    assert calendar_date is None


def test_scope_listing_generated_images_index_jsonl_kind_matches_accessor() -> None:
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.generated_images_index_jsonl
    kind, calendar_date = parse_memory_store_relative_path(rel)
    assert kind == CompanionMemoryDocumentKind.GENERATED_IMAGES_INDEX_JSONL
    assert calendar_date is None


def test_scope_listing_living_sphere_updates_jsonl_kind_matches_accessor() -> None:
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.living_sphere_updates_jsonl
    kind, calendar_date = parse_memory_store_relative_path(rel)
    assert kind == CompanionMemoryDocumentKind.LIVING_SPHERE_UPDATES_JSONL
    assert calendar_date is None


def test_scope_listing_techno_core_events_jsonl_kind_matches_accessor() -> None:
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.techno_core_events_jsonl
    kind, calendar_date = parse_memory_store_relative_path(rel)
    assert kind == CompanionMemoryDocumentKind.TECHNO_CORE_EVENTS_JSONL
    assert calendar_date is None


def test_scope_listing_ai_private_md_kind_matches_accessor() -> None:
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.ai_private_md
    kind, calendar_date = parse_memory_store_relative_path(rel)
    assert kind == CompanionMemoryDocumentKind.AI_PRIVATE_MD
    assert calendar_date is None
