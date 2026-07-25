from __future__ import annotations

from pathlib import Path

from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_path_constants import (
    ABOUT_MD_REL,
    AXIOM_MD_REL,
    BOOTSTRAP_MD_REL,
    BOOTSTRAP_TELEGRAM_PROFILE_MD_REL,
    CHANNELS_MD_REL,
    COMPANIONSHIP_MD_REL,
    COMPANION_DREAMING_STATE_JSON_REL,
    COMPANION_CONTEXT_COMPACTION_STATE_JSON_REL,
    COMPANION_LIVING_SPHERE_CURATOR_JSON_REL,
    COMPANION_SCHEDULE_TASKS_JSON_REL,
    CONTEXT_JSON_REL,
    HARNESS_MD_REL,
    IDENTITY_MD_REL,
    INTY_MD_REL,
    INTY_V2_CONTEXT_COMPACTION_STATE_JSON_REL,
    INTY_V2_DREAMING_STATE_JSON_REL,
    INTY_V2_LIVING_SPHERE_CURATOR_JSON_REL,
    INTY_V2_SCHEDULE_TASKS_JSON_REL,
    LIVING_SPHERE_MD_REL,
    MEMORY_DAILY_GIST_DIR_REL,
    MEMORY_MD_REL,
    OUTPUT_FORMAT_IM_DM_MD_REL,
    SAFETY_MD_REL,
    SIGNIFICANCE_PERCEPTION_MD_REL,
    SOUL_MD_REL,
    STYLE_MD_REL,
    TECHNO_CORE_MD_REL,
    TOOLS_MD_REL,
    TRANSCRIPT_INNER_TICK_JSONL_REL,
    TRANSCRIPT_JSONL_REL,
    USER_MD_REL,
    memory_daily_gist_rel,
)
from app.core.companion_harness.memory.memory_store_scope import (
    MemoryStoreScopePaths,
    ensure_minimal_documents_in_store,
    get_imate_axiom_system_text,
    get_inty_facts_system_text,
    get_safety_system_text,
    is_scope_initialized_in_store,
    load_template_seed_text,
)
from app.core.companion_harness.companion.scope import CompanionScope


def test_memory_store_scope_paths_properties() -> None:
    p = MemoryStoreScopePaths()
    assert p.identity == IDENTITY_MD_REL
    assert p.soul == SOUL_MD_REL
    assert p.style_md == STYLE_MD_REL
    assert p.user_md == USER_MD_REL
    assert p.memory_md == MEMORY_MD_REL
    assert p.channels_md == CHANNELS_MD_REL
    assert p.companionship_md == COMPANIONSHIP_MD_REL
    assert p.techno_core_md == TECHNO_CORE_MD_REL
    assert p.living_sphere_md == LIVING_SPHERE_MD_REL
    assert p.tools_md == TOOLS_MD_REL
    assert p.significance_perception_md == SIGNIFICANCE_PERCEPTION_MD_REL
    assert p.transcript == TRANSCRIPT_JSONL_REL
    assert p.transcript_inner_tick == TRANSCRIPT_INNER_TICK_JSONL_REL
    assert p.context_json == CONTEXT_JSON_REL
    assert p.memory_daily_gist("2026-04-05") == memory_daily_gist_rel("2026-04-05")
    assert memory_daily_gist_rel("2026-04-05").startswith(
        f"{MEMORY_DAILY_GIST_DIR_REL}/"
    )
    assert (
        p.living_sphere_curator_state_json
        == COMPANION_LIVING_SPHERE_CURATOR_JSON_REL
    )
    assert (
        p.context_compaction_state_json
        == COMPANION_CONTEXT_COMPACTION_STATE_JSON_REL
    )
    assert p.schedule_queue_json == COMPANION_SCHEDULE_TASKS_JSON_REL
    assert p.dreaming_state_json == COMPANION_DREAMING_STATE_JSON_REL


def test_doctrine_prompt_seed_getters_return_non_empty() -> None:
    for text in (
        get_imate_axiom_system_text(),
        get_inty_facts_system_text(),
        get_safety_system_text(),
    ):
        assert text.strip()


def test_package_prompt_seed_files_load_via_canonical_rel_paths() -> None:
    for rel in (
        ABOUT_MD_REL,
        AXIOM_MD_REL,
        BOOTSTRAP_MD_REL,
        BOOTSTRAP_TELEGRAM_PROFILE_MD_REL,
        CHANNELS_MD_REL,
        HARNESS_MD_REL,
        INTY_MD_REL,
        OUTPUT_FORMAT_IM_DM_MD_REL,
        SAFETY_MD_REL,
        TOOLS_MD_REL,
        SIGNIFICANCE_PERCEPTION_MD_REL,
    ):
        assert load_template_seed_text(rel).strip()


def test_memory_store_scope_paths_custom_state_file_prefix() -> None:
    p = MemoryStoreScopePaths(state_file_prefix=".inty_v2")
    assert (
        p.living_sphere_curator_state_json
        == INTY_V2_LIVING_SPHERE_CURATOR_JSON_REL
    )
    assert (
        p.context_compaction_state_json
        == INTY_V2_CONTEXT_COMPACTION_STATE_JSON_REL
    )
    assert p.schedule_queue_json == INTY_V2_SCHEDULE_TASKS_JSON_REL
    assert p.dreaming_state_json == INTY_V2_DREAMING_STATE_JSON_REL
    assert p.identity == IDENTITY_MD_REL
    assert p.transcript == TRANSCRIPT_JSONL_REL


def test_is_scope_initialized_in_store_complete(tmp_path: Path) -> None:
    root = tmp_path / "virt"
    root.mkdir()
    store = MemoryStore(
        scope=CompanionScope("mss", "a", str(root.resolve())),
        repository=None,
    )
    for name in (
        IDENTITY_MD_REL,
        SOUL_MD_REL,
        USER_MD_REL,
        MEMORY_MD_REL,
        TRANSCRIPT_JSONL_REL,
    ):
        store.write_document(name, "ok\n")
    assert is_scope_initialized_in_store(store) is True


def test_ensure_minimal_documents_in_store(tmp_path: Path) -> None:
    root = tmp_path / "seed_ws"
    root.mkdir()
    store = MemoryStore(
        scope=CompanionScope("mss", "a", str(root.resolve()) + "-seed"),
        repository=None,
    )
    assert is_scope_initialized_in_store(store) is False
    ensure_minimal_documents_in_store(store)
    assert is_scope_initialized_in_store(store) is True
    memory = store.read_document(MEMORY_MD_REL)
    assert "记忆库" in memory
    assert "42" not in memory
    assert "待对话填充" in store.read_document(USER_MD_REL)
    assert "沟通风格" in store.read_document(STYLE_MD_REL)
    assert "我们的关系" in store.read_document(COMPANIONSHIP_MD_REL)
    assert "Channels are medium" in store.read_document(CHANNELS_MD_REL)
    ensure_minimal_documents_in_store(store)
    assert is_scope_initialized_in_store(store) is True
