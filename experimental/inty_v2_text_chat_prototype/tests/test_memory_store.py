"""MemoryStore: cache/mirror/postgres/version behavior."""

from __future__ import annotations

import os
import socket
import sys
import tempfile
import unittest
from pathlib import Path

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.memory_store import (
    MemoryRecord,
    MemoryRepository,
    MemoryStore,
    PostgresMemoryRepository,
)


def _postgres_reachable(host: str = "127.0.0.1", port: int = 5432) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.3)
    try:
        s.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


class TestMemoryStore(unittest.TestCase):
    class _FakeRepo(MemoryRepository):
        def __init__(self) -> None:
            self.rows: dict[tuple[str, str], MemoryRecord] = {}

        def read_document(
            self,
            *,
            workspace_root: str,
            relative_path: str,
        ) -> MemoryRecord | None:
            return self.rows.get((workspace_root, relative_path))

        def upsert_document(
            self,
            *,
            workspace_root: str,
            record: MemoryRecord,
        ) -> None:
            key = (workspace_root, record.relative_path)
            cur = self.rows.get(key)
            if cur is None or cur.version <= record.version:
                self.rows[key] = record

        def max_version(
            self,
            *,
            workspace_root: str,
            relative_path: str,
        ) -> int:
            cur = self.rows.get((workspace_root, relative_path))
            return 0 if cur is None else cur.version

    def test_cache_write_and_mirror_read(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store = MemoryStore(
                workspace_root=root,
                repository=None,
                mirror_to_files=True,
                flush_batch_size=8,
            )
            store.write_document("USER.md", "# USER\n\nx\n")
            self.assertEqual(store.read_document("USER.md"), "# USER\n\nx\n")
            self.assertEqual((root / "USER.md").read_text(encoding="utf-8"), "# USER\n\nx\n")
            store.shutdown(timeout_s=2.0)

    def test_append_line_formats_newline(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store = MemoryStore(
                workspace_root=root,
                repository=None,
                mirror_to_files=True,
                flush_batch_size=8,
            )
            store.append_line("memory/daily/2099-01-01.md", "a")
            store.append_line("memory/daily/2099-01-01.md", "b")
            self.assertEqual(
                store.read_document("memory/daily/2099-01-01.md"),
                "a\nb\n",
            )
            store.shutdown(timeout_s=2.0)

    def test_recovery_from_repository(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ws = str(root.resolve())
            repo = self._FakeRepo()
            repo.upsert_document(
                workspace_root=ws,
                record=MemoryRecord(
                    relative_path="MEMORY.md",
                    content="# MEMORY\n\nfrom-repo\n",
                    version=7,
                    updated_at="2026-01-01T00:00:00+00:00",
                ),
            )
            store = MemoryStore(
                workspace_root=root,
                repository=repo,
                mirror_to_files=False,
                flush_batch_size=8,
            )
            self.assertEqual(store.read_document("MEMORY.md"), "# MEMORY\n\nfrom-repo\n")
            store.shutdown(timeout_s=2.0)

    def test_write_uses_repo_max_version(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ws = str(root.resolve())
            repo = self._FakeRepo()
            repo.upsert_document(
                workspace_root=ws,
                record=MemoryRecord(
                    relative_path="MEMORY.md",
                    content="new",
                    version=9,
                    updated_at="2026-01-01T00:00:00+00:00",
                ),
            )
            store = MemoryStore(
                workspace_root=root,
                repository=repo,
                mirror_to_files=False,
                flush_batch_size=8,
            )
            store.write_document("MEMORY.md", "newer")
            store.flush_now(timeout_s=5.0)
            row = repo.read_document(workspace_root=ws, relative_path="MEMORY.md")
            assert row is not None
            self.assertEqual(row.content, "newer")
            self.assertEqual(row.version, 10)
            store.shutdown(timeout_s=2.0)

    def test_postgres_flush_and_recovery(self) -> None:
        dsn = (os.getenv("INTY_V2_PROTO_MEMORY_PG_DSN") or "").strip()
        if not dsn or not _postgres_reachable():
            self.skipTest(
                "requires running postgres on 127.0.0.1:5432 and INTY_V2_PROTO_MEMORY_PG_DSN"
            )
        table = "proto_memory_docs_test"
        repo = PostgresMemoryRepository(dsn=dsn, table_name=table)
        repo.ensure_schema()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ws = str(root.resolve())
            store = MemoryStore(
                workspace_root=root,
                repository=repo,
                mirror_to_files=False,
                flush_batch_size=8,
            )
            store.write_document("USER.md", "# USER\n\npg-1\n")
            store.flush_now(timeout_s=5.0)
            row = repo.read_document(workspace_root=ws, relative_path="USER.md")
            assert row is not None
            self.assertEqual(row.content, "# USER\n\npg-1\n")
            self.assertEqual(row.version, 1)
            store.shutdown(timeout_s=2.0)

            store2 = MemoryStore(
                workspace_root=root,
                repository=repo,
                mirror_to_files=False,
                flush_batch_size=8,
            )
            self.assertEqual(store2.read_document("USER.md"), "# USER\n\npg-1\n")
            store2.shutdown(timeout_s=2.0)


if __name__ == "__main__":
    unittest.main()
