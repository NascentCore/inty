from __future__ import annotations

import datetime

import pytest

from app.core.companion_harness.memory.memory_store_document_mapping import (
    CompanionMemoryDocumentKind,
    parse_memory_store_relative_path,
    relative_path_for_kind,
)
from app.core.companion_harness.memory.memory_store_path_constants import (
    AI_PRIVATE_JSONL_REL,
    AI_PRIVATE_MD_REL,
    CHANNELS_MD_REL,
    COMPANION_CONTEXT_COMPACTION_STATE_JSON_REL,
    COMPANION_DREAMING_STATE_JSON_REL,
    COMPANION_LIVING_SPHERE_CURATOR_JSON_REL,
    COMPANION_RUNTIME_EVENTS_JSONL_REL,
    COMPANION_SCHEDULE_TASKS_JSON_REL,
    COMPANION_USER_FEEDBACK_JSONL_REL,
    COMPANIONSHIP_MD_REL,
    CONTEXT_JSON_REL,
    GENERATED_IMAGES_INDEX_JSONL_REL,
    IDENTITY_MD_REL,
    INTY_V2_CONTEXT_COMPACTION_STATE_JSON_REL,
    INTY_V2_DREAMING_STATE_JSON_REL,
    INTY_V2_LIVING_SPHERE_CURATOR_JSON_REL,
    INTY_V2_SCHEDULE_TASKS_JSON_REL,
    LIFE_CURRENTS_MD_REL,
    LIVING_SPHERE_MD_REL,
    LIVING_SPHERE_UPDATES_JSONL_REL,
    MEMORY_MD_REL,
    SIGNIFICANCE_PERCEPTION_MD_REL,
    SOUL_MD_REL,
    STYLE_MD_REL,
    TECHNO_CORE_EVENTS_JSONL_REL,
    TECHNO_CORE_MD_REL,
    TOOL_BACKGROUND_JSONL_REL,
    TOOLS_MD_REL,
    TRANSCRIPT_INNER_TICK_JSONL_REL,
    TRANSCRIPT_JSONL_REL,
    USER_MD_REL,
    memory_daily_gist_rel,
)
from app.core.companion_harness.memory.memory_store_scope import (
    MemoryStoreScopePaths,
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
        SOUL_MD_REL,
        STYLE_MD_REL,
        USER_MD_REL,
        MEMORY_MD_REL,
        LIFE_CURRENTS_MD_REL,
        CHANNELS_MD_REL,
        COMPANIONSHIP_MD_REL,
        TECHNO_CORE_MD_REL,
        TECHNO_CORE_EVENTS_JSONL_REL,
        LIVING_SPHERE_MD_REL,
        LIVING_SPHERE_UPDATES_JSONL_REL,
        TOOLS_MD_REL,
        SIGNIFICANCE_PERCEPTION_MD_REL,
        TRANSCRIPT_JSONL_REL,
        TRANSCRIPT_INNER_TICK_JSONL_REL,
        CONTEXT_JSON_REL,
        AI_PRIVATE_MD_REL,
        AI_PRIVATE_JSONL_REL,
        TOOL_BACKGROUND_JSONL_REL,
        GENERATED_IMAGES_INDEX_JSONL_REL,
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
    ):
        kind, cal = parse_memory_store_relative_path(rel)
        assert relative_path_for_kind(kind, cal) == rel


def test_invalid_path_raises() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        parse_memory_store_relative_path("memory/not-a-date.md")


def test_rel_to_kind_static_paths_match_scope_path_accessors() -> None:
    default_paths = MemoryStoreScopePaths()
    inty_v2_paths = MemoryStoreScopePaths(state_file_prefix=".inty_v2")
    rel_accessor_cases: tuple[tuple[str, MemoryStoreScopePaths, str], ...] = (
        (IDENTITY_MD_REL, default_paths, "identity"),
        (SOUL_MD_REL, default_paths, "soul"),
        (STYLE_MD_REL, default_paths, "style_md"),
        (USER_MD_REL, default_paths, "user_md"),
        (MEMORY_MD_REL, default_paths, "memory_md"),
        (LIFE_CURRENTS_MD_REL, default_paths, "life_currents_md"),
        (CHANNELS_MD_REL, default_paths, "channels_md"),
        (COMPANIONSHIP_MD_REL, default_paths, "companionship_md"),
        (TECHNO_CORE_MD_REL, default_paths, "techno_core_md"),
        (TECHNO_CORE_EVENTS_JSONL_REL, default_paths, "techno_core_events_jsonl"),
        (LIVING_SPHERE_MD_REL, default_paths, "living_sphere_md"),
        (
            LIVING_SPHERE_UPDATES_JSONL_REL,
            default_paths,
            "living_sphere_updates_jsonl",
        ),
        (TOOLS_MD_REL, default_paths, "tools_md"),
        (
            SIGNIFICANCE_PERCEPTION_MD_REL,
            default_paths,
            "significance_perception_md",
        ),
        (TRANSCRIPT_JSONL_REL, default_paths, "transcript"),
        (TRANSCRIPT_INNER_TICK_JSONL_REL, default_paths, "transcript_inner_tick"),
        (CONTEXT_JSON_REL, default_paths, "context_json"),
        (AI_PRIVATE_MD_REL, default_paths, "ai_private_md"),
        (AI_PRIVATE_JSONL_REL, default_paths, "ai_private_jsonl"),
        (TOOL_BACKGROUND_JSONL_REL, default_paths, "tool_background_jsonl"),
        (
            GENERATED_IMAGES_INDEX_JSONL_REL,
            default_paths,
            "generated_images_index_jsonl",
        ),
        (
            COMPANION_LIVING_SPHERE_CURATOR_JSON_REL,
            default_paths,
            "living_sphere_curator_state_json",
        ),
        (
            COMPANION_CONTEXT_COMPACTION_STATE_JSON_REL,
            default_paths,
            "context_compaction_state_json",
        ),
        (COMPANION_SCHEDULE_TASKS_JSON_REL, default_paths, "schedule_queue_json"),
        (
            COMPANION_RUNTIME_EVENTS_JSONL_REL,
            default_paths,
            "companion_runtime_events_jsonl",
        ),
        (
            COMPANION_USER_FEEDBACK_JSONL_REL,
            default_paths,
            "companion_user_feedback_jsonl",
        ),
        (COMPANION_DREAMING_STATE_JSON_REL, default_paths, "dreaming_state_json"),
        (
            INTY_V2_LIVING_SPHERE_CURATOR_JSON_REL,
            inty_v2_paths,
            "living_sphere_curator_state_json",
        ),
        (
            INTY_V2_CONTEXT_COMPACTION_STATE_JSON_REL,
            inty_v2_paths,
            "context_compaction_state_json",
        ),
        (INTY_V2_SCHEDULE_TASKS_JSON_REL, inty_v2_paths, "schedule_queue_json"),
        (INTY_V2_DREAMING_STATE_JSON_REL, inty_v2_paths, "dreaming_state_json"),
    )
    for rel, paths, attr in rel_accessor_cases:
        assert rel == getattr(paths, attr)
