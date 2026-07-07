from __future__ import annotations

from pathlib import Path

from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_path_constants import (
    CONTEXT_JSON_REL,
    IDENTITY_MD_REL,
    MEMORY_MD_REL,
    SOUL_MD_REL,
    TRANSCRIPT_JSONL_REL,
    USER_MD_REL,
)
from app.core.companion_harness.memory.memory_store_scope import (
    MemoryStoreScopePaths,
    ensure_minimal_documents_in_store,
    is_scope_initialized_in_store,
)
from app.core.companion_harness.companion.scope import CompanionScope


def test_memory_store_scope_paths_properties() -> None:
    p = MemoryStoreScopePaths()
    assert p.identity == "IDENTITY.md"
    assert p.soul == "SOUL.md"
    assert p.style_md == "STYLE.md"
    assert p.user_md == "USER.md"
    assert p.memory_md == "MEMORY.md"
    assert p.channels_md == "CHANNELS.md"
    assert p.companionship_md == "COMPANIONSHIP.md"
    assert p.techno_core_md == "TECHNO_CORE.md"
    assert p.living_sphere_md == "LIVING_SPHERE.md"
    assert p.tools_md == "TOOLS.md"
    assert p.transcript == TRANSCRIPT_JSONL_REL
    assert p.context_json == CONTEXT_JSON_REL
    assert p.memory_daily_gist("2026-04-05") == "memory/daily/2026-04-05.md"
    assert (
        p.living_sphere_curator_state_json
        == ".companion_living_sphere_curator.json"
    )
    assert (
        p.context_compaction_state_json
        == ".companion_context_compaction_state.json"
    )
    assert p.schedule_queue_json == ".companion_schedule_tasks.json"
    assert p.dreaming_state_json == ".companion_dreaming_state.json"


def test_memory_store_scope_paths_custom_state_file_prefix() -> None:
    p = MemoryStoreScopePaths(state_file_prefix=".inty_v2")
    assert (
        p.living_sphere_curator_state_json
        == ".inty_v2_living_sphere_curator.json"
    )
    assert p.schedule_queue_json == ".inty_v2_schedule_tasks.json"
    assert p.dreaming_state_json == ".inty_v2_dreaming_state.json"
    assert p.identity == "IDENTITY.md"
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
    memory = store.read_document("MEMORY.md")
    assert "记忆库" in memory
    assert "42" not in memory
    assert "待对话填充" in store.read_document("USER.md")
    assert "沟通风格" in store.read_document("STYLE.md")
    assert "我们的关系" in store.read_document("COMPANIONSHIP.md")
    assert "Channels are medium" in store.read_document("CHANNELS.md")
    ensure_minimal_documents_in_store(store)
    assert is_scope_initialized_in_store(store) is True
