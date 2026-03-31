"""DB-first append store for workspace JSONL event streams."""

from __future__ import annotations

import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any

from .file_store import append_line

_DEFAULT_TABLE_NAME = "proto_workspace_jsonl_events"
_LOCK = threading.Lock()
_REPOSITORIES: dict[str, "PostgresJsonlEventRepository"] = {}


class PostgresJsonlEventRepository:
    def __init__(self, *, dsn: str, table_name: str) -> None:
        self._dsn = dsn
        self._table_name = table_name

    def ensure_schema(self) -> None:
        import psycopg

        ddl = (
            f"CREATE TABLE IF NOT EXISTS {self._table_name} ("
            "sequence_id BIGSERIAL PRIMARY KEY, "
            "event_uuid TEXT NOT NULL UNIQUE, "
            "workspace_root TEXT NOT NULL, "
            "stream_name TEXT NOT NULL, "
            "payload_json JSONB NOT NULL, "
            "created_at TIMESTAMPTZ NOT NULL DEFAULT now()"
            ")"
        )
        idx = (
            f"CREATE INDEX IF NOT EXISTS idx_{self._table_name}_ws_stream_seq "
            f"ON {self._table_name} (workspace_root, stream_name, sequence_id DESC)"
        )
        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(ddl)
                cur.execute(idx)
            conn.commit()

    def append_event(
        self,
        *,
        workspace_root: str,
        stream_name: str,
        payload: dict[str, Any],
    ) -> None:
        import psycopg
        from psycopg.types.json import Jsonb

        sql = (
            f"INSERT INTO {self._table_name} "
            "(event_uuid, workspace_root, stream_name, payload_json) "
            "VALUES (%s, %s, %s, %s)"
        )
        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        str(uuid.uuid4()),
                        workspace_root,
                        stream_name,
                        Jsonb(payload),
                    ),
                )
            conn.commit()


def _dsn_and_table() -> tuple[str, str]:
    dsn = (os.getenv("INTY_V2_PROTO_JSONL_PG_DSN") or "").strip()
    if not dsn:
        dsn = (os.getenv("INTY_V2_PROTO_MEMORY_PG_DSN") or "").strip()
    table = (os.getenv("INTY_V2_PROTO_JSONL_PG_TABLE") or "").strip()
    if not table:
        table = _DEFAULT_TABLE_NAME
    return dsn, table


def _get_repository() -> PostgresJsonlEventRepository | None:
    dsn, table = _dsn_and_table()
    if not dsn:
        return None
    key = f"{dsn}::{table}"
    with _LOCK:
        cur = _REPOSITORIES.get(key)
        if cur is not None:
            return cur
        repo = PostgresJsonlEventRepository(dsn=dsn, table_name=table)
        repo.ensure_schema()
        _REPOSITORIES[key] = repo
        return repo


def append_jsonl_with_db(path: Path, record: dict[str, Any]) -> None:
    repo = _get_repository()
    if repo is not None:
        workspace_root = str(path.parent.resolve())
        repo.append_event(
            workspace_root=workspace_root,
            stream_name=path.name,
            payload=record,
        )
    append_line(path, json.dumps(record, ensure_ascii=False))


def flush_jsonl_db_store(*, timeout_s: float = 5.0) -> None:
    _ = timeout_s
    return


def shutdown_jsonl_db_store(*, timeout_s: float = 5.0) -> None:
    _ = timeout_s
    with _LOCK:
        _REPOSITORIES.clear()
