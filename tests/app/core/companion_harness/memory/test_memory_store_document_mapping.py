from __future__ import annotations

import datetime

import pytest

from app.core.companion_harness.memory.memory_store_document_mapping import (
    CompanionMemoryDocumentKind,
    parse_memory_store_relative_path,
    relative_path_for_kind,
)
from app.core.companion_harness.memory.memory_store_path_constants import (
    CHANNELS_MD_REL,
    COMPANION_CONTEXT_COMPACTION_STATE_JSON_REL,
    COMPANION_DREAMING_STATE_JSON_REL,
    COMPANION_LIVING_SPHERE_CURATOR_JSON_REL,
    COMPANION_RUNTIME_EVENTS_JSONL_REL,
    COMPANION_SCHEDULE_TASKS_JSON_REL,
    COMPANION_USER_FEEDBACK_JSONL_REL,
    COMPANIONSHIP_MD_REL,
    GENERATED_IMAGES_INDEX_JSONL_REL,
    IDENTITY_MD_REL,
    INTY_V2_CONTEXT_COMPACTION_STATE_JSON_REL,
    INTY_V2_DREAMING_STATE_JSON_REL,
    INTY_V2_LIVING_SPHERE_CURATOR_JSON_REL,
    INTY_V2_SCHEDULE_TASKS_JSON_REL,
    LIFE_CURRENTS_MD_REL,
    SOUL_MD_REL,
    STYLE_MD_REL,
    TECHNO_CORE_EVENTS_JSONL_REL,
    TOOL_BACKGROUND_JSONL_REL,
    TRANSCRIPT_INNER_TICK_JSONL_REL,
    TRANSCRIPT_JSONL_REL,
    memory_daily_gist_rel,
)


def test_parse_identity_and_daily() -> None:
    k, d = parse_memory_store_relative_path(IDENTITY_MD_REL)
    assert k == CompanionMemoryDocumentKind.IDENTITY
    assert d is None
    k2, d2 = parse_memory_store_relative_path(memory_daily_gist_rel("2026-03-01"))
    assert k2 == CompanionMemoryDocumentKind.MEMORY_DAILY_RAW
    assert d2 == datetime.date(2026, 3, 1)


def test_roundtrip_static_paths() -> None:
    for rel in (
        IDENTITY_MD_REL,
        CHANNELS_MD_REL,
        COMPANIONSHIP_MD_REL,
        LIFE_CURRENTS_MD_REL,
        SOUL_MD_REL,
        STYLE_MD_REL,
        TRANSCRIPT_JSONL_REL,
        TRANSCRIPT_INNER_TICK_JSONL_REL,
        TOOL_BACKGROUND_JSONL_REL,
        COMPANION_LIVING_SPHERE_CURATOR_JSON_REL,
        COMPANION_CONTEXT_COMPACTION_STATE_JSON_REL,
        COMPANION_SCHEDULE_TASKS_JSON_REL,
        COMPANION_RUNTIME_EVENTS_JSONL_REL,
        COMPANION_USER_FEEDBACK_JSONL_REL,
        COMPANION_DREAMING_STATE_JSON_REL,
        INTY_V2_LIVING_SPHERE_CURATOR_JSON_REL,
        INTY_V2_CONTEXT_COMPACTION_STATE_JSON_REL,
        INTY_V2_SCHEDULE_TASKS_JSON_REL,
        INTY_V2_DREAMING_STATE_JSON_REL,
        GENERATED_IMAGES_INDEX_JSONL_REL,
        TECHNO_CORE_EVENTS_JSONL_REL,
    ):
        kind, cal = parse_memory_store_relative_path(rel)
        assert relative_path_for_kind(kind, cal) == rel


def test_invalid_path_raises() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        parse_memory_store_relative_path("memory/not-a-date.md")
