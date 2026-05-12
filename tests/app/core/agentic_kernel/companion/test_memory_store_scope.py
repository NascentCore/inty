from __future__ import annotations

from pathlib import Path

from app.core.agentic_kernel.companion.memory_store import MemoryStore
from app.core.agentic_kernel.companion.memory_store_scope import (
    MemoryStoreScopePaths,
    ensure_minimal_documents_in_store,
    is_scope_initialized_in_store,
    is_scope_initialized_on_disk,
)
from app.core.agentic_kernel.companion.scope import CompanionScope

def test_memory_store_scope_paths_properties() -> None:
    p = MemoryStoreScopePaths()
    assert p.identity == "IDENTITY.md"
    assert p.soul == "SOUL.md"
    assert p.user_md == "USER.md"
    assert p.memory_md == "MEMORY.md"
    assert p.living_sphere_md == "LIVING_SPHERE.md"
    assert p.tools_md == "TOOLS.md"
    assert p.transcript == "transcript.jsonl"
    assert p.context_json == "context.json"
    assert p.memory_dir == "memory"
    assert p.memory_daily_dir == "memory/daily"
    assert p.memory_raw_diary("2026-04-05") == "memory/daily/2026-04-05.md"
    assert p.memory_day_summary("2026-04-05") == "memory/2026-04-05.md"
    assert p.memory_pipeline_state_json == ".companion_memory_pipeline.json"
    assert p.context_compaction_state_json == ".companion_context_compaction_state.json"
    assert p.schedule_queue_json == ".companion_schedule_tasks.json"


def test_is_scope_initialized_on_disk_empty(tmp_path: Path) -> None:
    d = tmp_path / "empty"
    d.mkdir()
    assert is_scope_initialized_on_disk(d) is False


def test_is_scope_initialized_on_disk_complete(tmp_path: Path) -> None:
    d = tmp_path / "full"
    d.mkdir()
    for name in (
        "IDENTITY.md",
        "SOUL.md",
        "USER.md",
        "MEMORY.md",
        "transcript.jsonl",
    ):
        (d / name).write_text("x", encoding="utf-8")
    assert is_scope_initialized_on_disk(d) is True


def test_memory_store_scope_paths_custom_state_file_prefix() -> None:
    p = MemoryStoreScopePaths(state_file_prefix=".inty_v2")
    assert p.memory_pipeline_state_json == ".inty_v2_memory_pipeline.json"
    assert p.schedule_queue_json == ".inty_v2_schedule_tasks.json"
    assert p.identity == "IDENTITY.md"
    assert p.transcript == "transcript.jsonl"


def test_is_scope_initialized_in_store_complete(tmp_path: Path) -> None:
    root = tmp_path / "virt"
    root.mkdir()
    store = MemoryStore(
        scope=CompanionScope("mss", "a", str(root.resolve())),
        repository=None,
    )
    for name in (
        "IDENTITY.md",
        "SOUL.md",
        "USER.md",
        "MEMORY.md",
        "transcript.jsonl",
    ):
        store.write_document(name, "ok\n")
    assert is_scope_initialized_in_store(store) is True
    assert is_scope_initialized_on_disk(root) is False


def test_is_scope_initialized_on_disk_partial(tmp_path: Path) -> None:
    d = tmp_path / "partial"
    d.mkdir()
    for name in ("IDENTITY.md", "SOUL.md", "USER.md", "MEMORY.md"):
        (d / name).write_text("x", encoding="utf-8")
    assert is_scope_initialized_on_disk(d) is False


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
    ensure_minimal_documents_in_store(store)
    assert is_scope_initialized_in_store(store) is True
