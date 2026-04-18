"""DB-first JSONL append store behavior."""

from __future__ import annotations

import os
import socket
import sys
import tempfile
import unittest
from pathlib import Path

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_repl.jsonl_db_store import (
    PostgresJsonlEventRepository,
    append_jsonl_with_db,
    shutdown_jsonl_db_store,
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


class TestJsonlDbStore(unittest.TestCase):
    def test_append_jsonl_with_db_persists_payload_jsonb(self) -> None:
        dsn = (os.getenv("INTY_V2_PROTO_MEMORY_PG_DSN") or "").strip()
        if not dsn or not _postgres_reachable():
            self.skipTest(
                "requires running postgres on 127.0.0.1:5432 and INTY_V2_PROTO_MEMORY_PG_DSN"
            )
        table = "proto_workspace_jsonl_events_test"
        old_dsn = os.getenv("INTY_V2_PROTO_JSONL_PG_DSN")
        old_table = os.getenv("INTY_V2_PROTO_JSONL_PG_TABLE")
        os.environ["INTY_V2_PROTO_JSONL_PG_DSN"] = dsn
        os.environ["INTY_V2_PROTO_JSONL_PG_TABLE"] = table
        repo = PostgresJsonlEventRepository(dsn=dsn, table_name=table)
        repo.ensure_schema()

        try:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td).resolve()
                path = root / "tool_background.jsonl"
                payload = {
                    "kind": "tool_background_done",
                    "user_msg_uuid": "u1",
                    "assistant_msg_uuid": "a1",
                    "elapsed_ms": 12,
                }
                append_jsonl_with_db(path, payload)
                body = path.read_text(encoding="utf-8")
                self.assertIn('"kind": "tool_background_done"', body)

                import psycopg

                sql = (
                    f"SELECT stream_name, payload_json->>'kind' "
                    f"FROM {table} "
                    "WHERE workspace_root = %s "
                    "ORDER BY sequence_id DESC LIMIT 1"
                )
                with psycopg.connect(dsn) as conn:
                    with conn.cursor() as cur:
                        cur.execute(sql, (str(root),))
                        row = cur.fetchone()
                assert row is not None
                stream_name, kind = row
                self.assertEqual(stream_name, "tool_background.jsonl")
                self.assertEqual(kind, "tool_background_done")
        finally:
            if old_dsn is None:
                os.environ.pop("INTY_V2_PROTO_JSONL_PG_DSN", None)
            else:
                os.environ["INTY_V2_PROTO_JSONL_PG_DSN"] = old_dsn
            if old_table is None:
                os.environ.pop("INTY_V2_PROTO_JSONL_PG_TABLE", None)
            else:
                os.environ["INTY_V2_PROTO_JSONL_PG_TABLE"] = old_table
            shutdown_jsonl_db_store(timeout_s=1.0)


if __name__ == "__main__":
    unittest.main()
