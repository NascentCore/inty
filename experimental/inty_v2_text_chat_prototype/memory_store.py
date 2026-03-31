"""Memory semantic store: DB-authoritative append-only versions + file mirror."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .file_store import read_text, write_text_atomic
from .utc import utc_iso_ts


@dataclass(frozen=True)
class MemoryRecord:
    record_uuid: str
    sequence_id: int
    relative_path: str
    content: str
    created_at: str


class MemoryRepository(Protocol):
    def read_document(
        self,
        *,
        workspace_root: str,
        relative_path: str,
    ) -> MemoryRecord | None: ...

    def append_document(
        self,
        *,
        workspace_root: str,
        relative_path: str,
        content: str,
        record_uuid: str,
    ) -> MemoryRecord: ...


class PostgresMemoryRepository:
    """PostgreSQL append-only persistence for memory documents."""

    def __init__(
        self,
        *,
        dsn: str,
        table_name: str = "proto_memory_doc_versions",
    ) -> None:
        self._dsn = dsn
        self._table_name = table_name

    def ensure_schema(self) -> None:
        import psycopg

        ddl = (
            f"CREATE TABLE IF NOT EXISTS {self._table_name} ("
            "sequence_id BIGSERIAL PRIMARY KEY, "
            "record_uuid TEXT NOT NULL UNIQUE, "
            "workspace_root TEXT NOT NULL, "
            "relative_path TEXT NOT NULL, "
            "content TEXT NOT NULL, "
            "created_at TIMESTAMPTZ NOT NULL DEFAULT now()"
            ")"
        )
        idx = (
            f"CREATE INDEX IF NOT EXISTS idx_{self._table_name}_ws_rel_seq "
            f"ON {self._table_name} (workspace_root, relative_path, sequence_id DESC)"
        )
        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(ddl)
                cur.execute(idx)
            conn.commit()

    def read_document(
        self,
        *,
        workspace_root: str,
        relative_path: str,
    ) -> MemoryRecord | None:
        import psycopg

        sql = (
            f"SELECT record_uuid, sequence_id, content, created_at::text "
            f"FROM {self._table_name} "
            "WHERE workspace_root = %s AND relative_path = %s "
            "ORDER BY sequence_id DESC LIMIT 1"
        )
        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (workspace_root, relative_path))
                row = cur.fetchone()
        if row is None:
            return None
        record_uuid, sequence_id, content, created_at = row
        return MemoryRecord(
            record_uuid=str(record_uuid),
            sequence_id=int(sequence_id),
            relative_path=relative_path,
            content=str(content),
            created_at=str(created_at),
        )

    def append_document(
        self,
        *,
        workspace_root: str,
        relative_path: str,
        content: str,
        record_uuid: str,
    ) -> MemoryRecord:
        import psycopg

        sql = (
            f"INSERT INTO {self._table_name} "
            "(record_uuid, workspace_root, relative_path, content) "
            "VALUES (%s, %s, %s, %s) "
            "RETURNING sequence_id, created_at::text"
        )
        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (record_uuid, workspace_root, relative_path, content))
                row = cur.fetchone()
            conn.commit()
        assert row is not None
        sequence_id, created_at = row
        return MemoryRecord(
            record_uuid=record_uuid,
            sequence_id=int(sequence_id),
            relative_path=relative_path,
            content=content,
            created_at=str(created_at),
        )


class MemoryCache:
    """Thread-safe in-memory snapshot for one workspace."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: dict[str, MemoryRecord] = {}

    def get(self, relative_path: str) -> MemoryRecord | None:
        with self._lock:
            return self._records.get(relative_path)

    def put_committed(self, record: MemoryRecord) -> MemoryRecord:
        with self._lock:
            cur = self._records.get(record.relative_path)
            if cur is not None and record.sequence_id < cur.sequence_id:
                return cur
            self._records[record.relative_path] = record
            return record


class MemoryFileMirror:
    """Mirror memory records back to workspace files for local observability."""

    def __init__(self, *, workspace_root: Path, enabled: bool) -> None:
        self._root = workspace_root.resolve()
        self._enabled = enabled

    def _absolute(self, relative_path: str) -> Path:
        rel = relative_path.strip().replace("\\", "/")
        if rel.startswith("/"):
            raise ValueError("relative_path must be workspace-relative")
        p = (self._root / rel).resolve()
        p.relative_to(self._root)
        return p

    def read_if_exists(self, *, relative_path: str) -> str | None:
        if not self._enabled:
            return None
        p = self._absolute(relative_path)
        if not p.is_file():
            return None
        return read_text(p)

    def write(self, *, record: MemoryRecord) -> None:
        if not self._enabled:
            return
        write_text_atomic(self._absolute(record.relative_path), record.content)


class MemoryStore:
    """DB-authoritative memory store with optional file mirror."""

    def __init__(
        self,
        *,
        workspace_root: Path,
        repository: MemoryRepository | None,
        mirror_to_files: bool,
        flush_batch_size: int,
    ) -> None:
        self._workspace_root = workspace_root.resolve()
        self._workspace_root_str = str(self._workspace_root)
        self._cache = MemoryCache()
        self._mirror = MemoryFileMirror(
            workspace_root=self._workspace_root,
            enabled=mirror_to_files,
        )
        self._repository = repository
        self._flush_batch_size = flush_batch_size

    def _normalize_relative_path(self, relative_path: str) -> str:
        rel = (relative_path or "").strip().replace("\\", "/")
        if not rel:
            raise ValueError("relative_path must be non-empty")
        if rel.startswith("/"):
            raise ValueError("relative_path must be workspace-relative")
        abs_path = (self._workspace_root / rel).resolve()
        return abs_path.relative_to(self._workspace_root).as_posix()

    def _next_local_sequence(self, relative_path: str) -> int:
        cur = self._cache.get(relative_path)
        if cur is not None:
            return cur.sequence_id + 1
        mirrored = self._mirror.read_if_exists(relative_path=relative_path)
        if mirrored is None:
            return 1
        return 1

    def read_document_if_exists(self, relative_path: str) -> str | None:
        rel = self._normalize_relative_path(relative_path)
        cached = self._cache.get(rel)
        if cached is not None:
            return cached.content

        if self._repository is not None:
            rec = self._repository.read_document(
                workspace_root=self._workspace_root_str,
                relative_path=rel,
            )
            if rec is not None:
                loaded = self._cache.put_committed(rec)
                self._mirror.write(record=loaded)
                return loaded.content

        mirrored = self._mirror.read_if_exists(relative_path=rel)
        if mirrored is None:
            return None
        local_record = MemoryRecord(
            record_uuid=str(uuid.uuid4()),
            sequence_id=0,
            relative_path=rel,
            content=mirrored,
            created_at=utc_iso_ts(),
        )
        self._cache.put_committed(local_record)
        return mirrored

    def read_document(self, relative_path: str) -> str:
        body = self.read_document_if_exists(relative_path)
        if body is None:
            raise FileNotFoundError(
                f"memory document not found: {self._workspace_root / relative_path}"
            )
        return body

    def write_document(self, relative_path: str, content: str) -> None:
        rel = self._normalize_relative_path(relative_path)
        new_record_uuid = str(uuid.uuid4())
        if self._repository is not None:
            committed = self._repository.append_document(
                workspace_root=self._workspace_root_str,
                relative_path=rel,
                content=content,
                record_uuid=new_record_uuid,
            )
        else:
            committed = MemoryRecord(
                record_uuid=new_record_uuid,
                sequence_id=self._next_local_sequence(rel),
                relative_path=rel,
                content=content,
                created_at=utc_iso_ts(),
            )
        applied = self._cache.put_committed(committed)
        self._mirror.write(record=applied)

    def append_line(self, relative_path: str, line: str) -> None:
        rel = self._normalize_relative_path(relative_path)
        cur = self.read_document_if_exists(rel)
        if cur is None:
            cur = ""
        merged = cur
        if merged and not merged.endswith("\n"):
            merged += "\n"
        merged += line
        if not line.endswith("\n"):
            merged += "\n"
        self.write_document(rel, merged)

    def flush_now(self, *, timeout_s: float = 5.0) -> None:
        _ = timeout_s
        return

    def shutdown(self, *, timeout_s: float = 5.0) -> None:
        _ = timeout_s
        return
