from __future__ import annotations

import pytest

from app.core.companion_harness.memory.memory_store import (
    MemoryCache,
    MemoryRecord,
    MemoryStore,
    normalize_memory_store_relative_path,
)
from app.core.companion_harness.companion.scope import CompanionScope


def _scope(tmp_name: str) -> CompanionScope:
    return CompanionScope("mem-store-test", "agent", tmp_name)


def test_normalize_memory_store_relative_path_basic() -> None:
    assert normalize_memory_store_relative_path("a/b") == "a/b"
    assert normalize_memory_store_relative_path("a/./b") == "a/b"


def test_normalize_memory_store_relative_path_rejects_empty() -> None:
    with pytest.raises(ValueError):
        normalize_memory_store_relative_path("")
    with pytest.raises(ValueError):
        normalize_memory_store_relative_path("   ")
    with pytest.raises(ValueError):
        normalize_memory_store_relative_path(".")


def test_normalize_memory_store_relative_path_rejects_absolute() -> None:
    with pytest.raises(ValueError):
        normalize_memory_store_relative_path("/etc/passwd")


def test_normalize_memory_store_relative_path_rejects_escape() -> None:
    with pytest.raises(ValueError):
        normalize_memory_store_relative_path("../x")


def test_memory_store_write_read_in_memory(tmp_path) -> None:
    store = MemoryStore(scope=_scope(tmp_path.name), repository=None)
    store.write_document("notes/x.md", "hello")
    assert store.read_document("notes/x.md") == "hello"


def test_memory_store_read_nonexistent(tmp_path) -> None:
    store = MemoryStore(scope=_scope(tmp_path.name), repository=None)
    with pytest.raises(FileNotFoundError):
        store.read_document("missing.md")


def test_memory_store_read_if_exists_none(tmp_path) -> None:
    store = MemoryStore(scope=_scope(tmp_path.name), repository=None)
    assert store.read_document_if_exists("nope.md") is None


def test_memory_store_append_jsonl_record(tmp_path) -> None:
    store = MemoryStore(scope=_scope(tmp_path.name), repository=None)
    store.append_jsonl_record("transcript.jsonl", {"role": "user", "content": "a"})
    store.append_jsonl_record("transcript.jsonl", {"role": "assistant", "content": "b"})
    body = store.read_document("transcript.jsonl")
    lines = [ln for ln in body.splitlines() if ln.strip()]
    assert len(lines) == 2


def test_memory_store_uses_repository_without_scope_disk_predicate(
    tmp_path,
) -> None:
    class _DummyRepo:
        def list_all_relative_paths(self) -> list[str]:
            return []

    s_repo = MemoryStore(scope=_scope(tmp_path.name), repository=_DummyRepo())
    assert s_repo.uses_repository_without_scope_disk is True
    s_no_repo = MemoryStore(scope=_scope(tmp_path.name + "-2"), repository=None)
    assert s_no_repo.uses_repository_without_scope_disk is False


def test_memory_store_no_disk_files(tmp_path) -> None:
    store = MemoryStore(scope=_scope(tmp_path.name), repository=None)
    store.write_document("SOUL.md", "# soul\n")
    assert store.read_document("SOUL.md") == "# soul\n"


def test_memory_store_append_line(tmp_path) -> None:
    store = MemoryStore(scope=_scope(tmp_path.name), repository=None)
    store.append_line("log.txt", "line1")
    store.append_line("log.txt", "line2")
    assert store.read_document("log.txt") == "line1\nline2\n"


def test_memory_store_iter_stored_relative_paths_in_memory(tmp_path) -> None:
    store = MemoryStore(scope=_scope(tmp_path.name), repository=None)
    store.write_document("A.md", "a")
    store.write_document("b/B.md", "b")
    paths = store.iter_stored_relative_paths()
    assert "A.md" in paths
    assert "b/B.md" in paths


def test_memory_cache_put_get() -> None:
    c = MemoryCache()
    r = MemoryRecord(
        record_uuid="u1",
        sequence_id=1,
        relative_path="x.md",
        content="hi",
        created_at="t",
    )
    c.put_committed(r)
    got = c.get("x.md")
    assert got is not None
    assert got.content == "hi"
