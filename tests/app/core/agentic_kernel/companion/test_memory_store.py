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


def test_memory_store_append_jsonl_record(tmp_path: Path) -> None:
    store = MemoryStore(
        workspace_root=tmp_path,
        repository=None,
        mirror_to_files=False,
        allow_workspace_disk_fallback=False,
    )
    store.append_jsonl_record("transcript.jsonl", {"role": "user", "content": "a"})
    store.append_jsonl_record("transcript.jsonl", {"role": "assistant", "content": "b"})
    body = store.read_document("transcript.jsonl")
    lines = [ln for ln in body.splitlines() if ln.strip()]
    assert len(lines) == 2


def test_memory_store_uses_repository_without_workspace_disk_predicate(
    tmp_path: Path,
) -> None:
    class _DummyRepo:
        pass

    s_repo = MemoryStore(
        workspace_root=tmp_path,
        repository=_DummyRepo(),
        mirror_to_files=False,
        allow_workspace_disk_fallback=False,
    )
    assert s_repo.uses_repository_without_workspace_disk is True
    s_allow = MemoryStore(
        workspace_root=tmp_path,
        repository=_DummyRepo(),
        mirror_to_files=False,
        allow_workspace_disk_fallback=True,
    )
    assert s_allow.uses_repository_without_workspace_disk is False
    s_no_repo = MemoryStore(
        workspace_root=tmp_path,
        repository=None,
        mirror_to_files=False,
        allow_workspace_disk_fallback=False,
    )
    assert s_no_repo.uses_repository_without_workspace_disk is False


def test_memory_store_production_no_mirror_no_fallback_no_disk_files(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        workspace_root=tmp_path,
        repository=None,
        mirror_to_files=False,
        allow_workspace_disk_fallback=False,
    )
    store.write_document("SOUL.md", "# soul\n")
    assert not (tmp_path / "SOUL.md").is_file()
    assert store.read_document("SOUL.md") == "# soul\n"


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
