from __future__ import annotations

from pathlib import Path

import pytest

from app.core.agentic_kernel.companion.memory_store import MemoryCache, MemoryRecord, MemoryStore


def test_memory_store_write_read_file_mirror(tmp_path: Path) -> None:
    store = MemoryStore(
        workspace_root=tmp_path,
        repository=None,
        mirror_to_files=True,
    )
    store.write_document("notes/x.md", "hello mirror")
    assert (tmp_path / "notes" / "x.md").read_text(encoding="utf-8") == "hello mirror"
    assert store.read_document("notes/x.md") == "hello mirror"


def test_memory_store_read_nonexistent(tmp_path: Path) -> None:
    store = MemoryStore(
        workspace_root=tmp_path,
        repository=None,
        mirror_to_files=True,
    )
    with pytest.raises(FileNotFoundError):
        store.read_document("missing.md")


def test_memory_store_read_if_exists_none(tmp_path: Path) -> None:
    store = MemoryStore(
        workspace_root=tmp_path,
        repository=None,
        mirror_to_files=True,
    )
    assert store.read_document_if_exists("nope.md") is None


def test_memory_store_append_line(tmp_path: Path) -> None:
    store = MemoryStore(
        workspace_root=tmp_path,
        repository=None,
        mirror_to_files=True,
    )
    store.append_line("log.txt", "line1")
    store.append_line("log.txt", "line2")
    assert store.read_document("log.txt") == "line1\nline2\n"


def test_memory_cache_put_get() -> None:
    c = MemoryCache()
    r = MemoryRecord(
        record_uuid="u1",
        sequence_id=1,
        relative_path="a.md",
        content="body",
        created_at="2026-01-01T00:00:00+00:00",
    )
    assert c.put_committed(r) == r
    got = c.get("a.md")
    assert got is not None
    assert got.content == "body"
    assert got.sequence_id == 1
