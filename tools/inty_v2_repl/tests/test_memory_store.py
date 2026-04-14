"""MemoryStore: cache / postgres / version behavior."""

from __future__ import annotations

import os
import socket
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.memory_store import (
    MemoryRecord,
    MemoryRepository,
    MemoryStore,
    SqlAlchemyMemoryRepository,
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
            self.rows: dict[tuple[str, str], list[MemoryRecord]] = {}
            self._sequence = 0

        def read_document(
            self,
            *,
            workspace_root: str,
            relative_path: str,
        ) -> MemoryRecord | None:
            history = self.rows.get((workspace_root, relative_path))
            if not history:
                return None
            return history[-1]

        def append_document(
            self,
            *,
            workspace_root: str,
            relative_path: str,
            content: str,
            record_uuid: str,
        ) -> MemoryRecord:
            self._sequence += 1
            row = MemoryRecord(
                record_uuid=record_uuid,
                sequence_id=self._sequence,
                relative_path=relative_path,
                content=content,
                created_at="2026-01-01T00:00:00+00:00",
            )
            key = (workspace_root, relative_path)
            history = self.rows.setdefault(key, [])
            history.append(row)
            return row

        def list_all_relative_paths(self, *, workspace_root: str) -> list[str]:
            return sorted(
                {rp for (ws, rp) in self.rows if ws == workspace_root},
            )

        def history(
            self,
            *,
            workspace_root: str,
            relative_path: str,
        ) -> list[MemoryRecord]:
            return list(self.rows.get((workspace_root, relative_path), []))

    def test_cache_write_in_memory_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store = MemoryStore(
                workspace_root=root,
                repository=None,
            )
            store.write_document("USER.md", "# USER\n\nx\n")
            self.assertEqual(store.read_document("USER.md"), "# USER\n\nx\n")
            self.assertFalse((root / "USER.md").exists())
            store.shutdown(timeout_s=2.0)

    def test_append_line_formats_newline(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store = MemoryStore(
                workspace_root=root,
                repository=None,
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
            repo.append_document(
                workspace_root=ws,
                relative_path="MEMORY.md",
                content="# MEMORY\n\nfrom-repo\n",
                record_uuid=str(uuid.uuid4()),
            )
            store = MemoryStore(
                workspace_root=root,
                repository=repo,
            )
            self.assertEqual(
                store.read_document("MEMORY.md"), "# MEMORY\n\nfrom-repo\n"
            )
            store.shutdown(timeout_s=2.0)

    def test_write_appends_history_and_reads_latest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ws = str(root.resolve())
            repo = self._FakeRepo()
            store = MemoryStore(
                workspace_root=root,
                repository=repo,
            )
            store.write_document("MEMORY.md", "v1")
            store.write_document("MEMORY.md", "v2")
            store.flush_now(timeout_s=5.0)
            rows = repo.history(workspace_root=ws, relative_path="MEMORY.md")
            self.assertEqual(len(rows), 2)
            self.assertNotEqual(rows[0].record_uuid, rows[1].record_uuid)
            self.assertLess(rows[0].sequence_id, rows[1].sequence_id)
            self.assertEqual(store.read_document("MEMORY.md"), "v2")
            store.shutdown(timeout_s=2.0)

    def test_postgres_flush_and_recovery(self) -> None:
        dsn = (os.getenv("INTY_V2_PROTO_MEMORY_PG_DSN") or "").strip()
        if not dsn or not _postgres_reachable():
            self.skipTest(
                "requires running postgres on 127.0.0.1:5432 and INTY_V2_PROTO_MEMORY_PG_DSN"
            )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "u_pg_test" / "agent_pg_test" / "chat_pg_test"
            root.mkdir(parents=True)
            ws = str(root.resolve())
            repo = SqlAlchemyMemoryRepository(
                user_id="u_pg_test",
                companion_id="agent_pg_test",
                chat_id="chat_pg_test",
            )
            store = MemoryStore(
                workspace_root=root,
                repository=repo,
            )
            store.write_document("USER.md", "# USER\n\npg-1\n")
            store.write_document("USER.md", "# USER\n\npg-2\n")
            store.flush_now(timeout_s=5.0)
            row = repo.read_document(workspace_root=ws, relative_path="USER.md")
            assert row is not None
            self.assertEqual(row.content, "# USER\n\npg-2\n")
            self.assertGreaterEqual(row.sequence_id, 1)
            store.shutdown(timeout_s=2.0)

            store2 = MemoryStore(
                workspace_root=root,
                repository=repo,
            )
            self.assertEqual(store2.read_document("USER.md"), "# USER\n\npg-2\n")
            store2.shutdown(timeout_s=2.0)


if __name__ == "__main__":
    unittest.main()
