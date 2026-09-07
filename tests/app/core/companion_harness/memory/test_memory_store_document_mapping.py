"""Tests for memory store document kind mapping."""

from __future__ import annotations

import datetime

import pytest

from app.core.companion_harness.memory.memory_store_document_mapping import (
    CompanionMemoryDocumentKind,
    parse_memory_store_relative_path,
    relative_path_for_kind,
)
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
    MemoryStoreScopePaths,
)

_DEFAULT_SCOPE_PATHS = DEFAULT_MEMORY_STORE_SCOPE_PATHS
_INTY_V2_SCOPE_PATHS = MemoryStoreScopePaths(state_file_prefix=".inty_v2")

# Mapped static paths exercised by parse/relative_path_for_kind roundtrip.
_SCOPE_PATH_ACCESSOR_CASES: tuple[tuple[MemoryStoreScopePaths, str], ...] = (
    (_DEFAULT_SCOPE_PATHS, "identity"),
    (_DEFAULT_SCOPE_PATHS, "soul"),
    (_DEFAULT_SCOPE_PATHS, "style_md"),
    (_DEFAULT_SCOPE_PATHS, "user_md"),
    (_DEFAULT_SCOPE_PATHS, "memory_md"),
    (_DEFAULT_SCOPE_PATHS, "life_currents_md"),
    (_DEFAULT_SCOPE_PATHS, "channels_md"),
    (_DEFAULT_SCOPE_PATHS, "companionship_md"),
    (_DEFAULT_SCOPE_PATHS, "techno_core_md"),
    (_DEFAULT_SCOPE_PATHS, "techno_core_events_jsonl"),
    (_DEFAULT_SCOPE_PATHS, "living_sphere_md"),
    (_DEFAULT_SCOPE_PATHS, "living_sphere_updates_jsonl"),
    (_DEFAULT_SCOPE_PATHS, "tools_md"),
    (_DEFAULT_SCOPE_PATHS, "significance_perception_md"),
    (_DEFAULT_SCOPE_PATHS, "transcript"),
    (_DEFAULT_SCOPE_PATHS, "transcript_inner_tick"),
    (_DEFAULT_SCOPE_PATHS, "context_json"),
    (_DEFAULT_SCOPE_PATHS, "ai_private_md"),
    (_DEFAULT_SCOPE_PATHS, "ai_private_jsonl"),
    (_DEFAULT_SCOPE_PATHS, "tool_background_jsonl"),
    (_DEFAULT_SCOPE_PATHS, "generated_images_index_jsonl"),
    (_DEFAULT_SCOPE_PATHS, "living_sphere_curator_state_json"),
    (_DEFAULT_SCOPE_PATHS, "context_compaction_state_json"),
    (_DEFAULT_SCOPE_PATHS, "schedule_queue_json"),
    (_DEFAULT_SCOPE_PATHS, "companion_runtime_events_jsonl"),
    (_DEFAULT_SCOPE_PATHS, "companion_user_feedback_jsonl"),
    (_DEFAULT_SCOPE_PATHS, "dreaming_state_json"),
    (_INTY_V2_SCOPE_PATHS, "living_sphere_curator_state_json"),
    (_INTY_V2_SCOPE_PATHS, "context_compaction_state_json"),
    (_INTY_V2_SCOPE_PATHS, "schedule_queue_json"),
    (_INTY_V2_SCOPE_PATHS, "dreaming_state_json"),
)


def test_parse_identity_and_daily() -> None:
    identity_rel = _DEFAULT_SCOPE_PATHS.identity
    kind, day = parse_memory_store_relative_path(identity_rel)
    assert kind == CompanionMemoryDocumentKind.IDENTITY
    assert day is None
    daily_rel = _DEFAULT_SCOPE_PATHS.memory_daily_gist("2026-03-01")
    kind2, day2 = parse_memory_store_relative_path(daily_rel)
    assert kind2 == CompanionMemoryDocumentKind.MEMORY_DAILY_RAW
    assert day2 == datetime.date(2026, 3, 1)


def test_roundtrip_static_paths() -> None:
    for paths, attr in _SCOPE_PATH_ACCESSOR_CASES:
        rel = getattr(paths, attr)
        kind, cal = parse_memory_store_relative_path(rel)
        assert relative_path_for_kind(kind, cal) == rel


def test_invalid_path_raises() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        parse_memory_store_relative_path("memory/not-a-date.md")


def test_rel_to_kind_static_paths_match_scope_path_accessors() -> None:
    for paths, attr in _SCOPE_PATH_ACCESSOR_CASES:
        rel = getattr(paths, attr)
        kind, cal = parse_memory_store_relative_path(rel)
        assert relative_path_for_kind(kind, cal) == rel
