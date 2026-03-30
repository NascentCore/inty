"""Memory semantic store: cache-first, async Postgres flush, optional file mirror."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from loguru import logger

from .file_store import read_text, write_text_atomic
from .utc import utc_iso_ts


@dataclass(frozen=True)
class MemoryRecord:
    relative_path: str
    content: str
    version: int
    updated_at: str


class MemoryRepository(Protocol):
    def read_document(
        self,
        *,
        workspace_root: str,
        relative_path: str,
    ) -> MemoryRecord | None: ...

    def upsert_document(
        self,
        *,
        workspace_root: str,
        record: MemoryRecord,
    ) -> None: ...

    def max_version(
        self,
        *,
        workspace_root: str,
        relative_path: str,
    ) -> int: ...


class PostgresMemoryRepository:
    """PostgreSQL persistence for memory documents."""

    def __init__(
        self,
        *,
        dsn: str,
        table_name: str = "proto_memory_docs",
    ) -> None:
        self._dsn = dsn
        self._table_name = table_name

    def ensure_schema(self) -> None:
        import psycopg

        ddl = (
            f"CREATE TABLE IF NOT EXISTS {self._table_name} ("
            "workspace_root TEXT NOT NULL, "
            "relative_path TEXT NOT NULL, "
            "content TEXT NOT NULL, "
            "version BIGINT NOT NULL, "
            "updated_at TIMESTAMPTZ NOT NULL, "
            "PRIMARY KEY (workspace_root, relative_path)"
            ")"
        )
        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(ddl)
            conn.commit()

    def read_document(
        self,
        *,
        workspace_root: str,
        relative_path: str,
    ) -> MemoryRecord | None:
        import psycopg

        sql = (
            f"SELECT content, version, updated_at::text FROM {self._table_name} "
            "WHERE workspace_root = %s AND relative_path = %s"
        )
        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (workspace_root, relative_path))
                row = cur.fetchone()
        if row is None:
            return None
        content, version, updated_at = row
        return MemoryRecord(
            relative_path=relative_path,
            content=str(content),
            version=int(version),
            updated_at=str(updated_at),
        )

    def upsert_document(
        self,
        *,
        workspace_root: str,
        record: MemoryRecord,
    ) -> None:
        import psycopg

        sql = (
            f"INSERT INTO {self._table_name} "
            "(workspace_root, relative_path, content, version, updated_at) "
            "VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT (workspace_root, relative_path) DO UPDATE SET "
            "content = EXCLUDED.content, "
            "version = EXCLUDED.version, "
            "updated_at = EXCLUDED.updated_at "
            f"WHERE {self._table_name}.version <= EXCLUDED.version"
        )
        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        workspace_root,
                        record.relative_path,
                        record.content,
                        record.version,
                        record.updated_at,
                    ),
                )
            conn.commit()

    def max_version(
        self,
        *,
        workspace_root: str,
        relative_path: str,
    ) -> int:
        import psycopg

        sql = (
            f"SELECT COALESCE(MAX(version), 0) FROM {self._table_name} "
            "WHERE workspace_root = %s AND relative_path = %s"
        )
        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (workspace_root, relative_path))
                row = cur.fetchone()
        if row is None:
            return 0
        return int(row[0] or 0)


class MemoryCache:
    """Thread-safe in-memory authoritative state for one workspace."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: dict[str, MemoryRecord] = {}

    def get(self, relative_path: str) -> MemoryRecord | None:
        with self._lock:
            return self._records.get(relative_path)

    def put(
        self,
        *,
        relative_path: str,
        content: str,
        version: int,
        updated_at: str,
    ) -> MemoryRecord:
        with self._lock:
            cur = self._records.get(relative_path)
            if cur is not None and version < cur.version:
                return cur
            rec = MemoryRecord(
                relative_path=relative_path,
                content=content,
                version=version,
                updated_at=updated_at,
            )
            self._records[relative_path] = rec
            return rec

    def write(self, *, relative_path: str, content: str) -> MemoryRecord:
        with self._lock:
            cur = self._records.get(relative_path)
            next_version = 1 if cur is None else cur.version + 1
            rec = MemoryRecord(
                relative_path=relative_path,
                content=content,
                version=next_version,
                updated_at=utc_iso_ts(),
            )
            self._records[relative_path] = rec
            return rec


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

    def exists(self, *, relative_path: str) -> bool:
        if not self._enabled:
            return False
        return self._absolute(relative_path).is_file()


@dataclass(frozen=True)
class _FlushItem:
    record: MemoryRecord


@dataclass(frozen=True)
class _FlushBarrier:
    done: threading.Event


class MemoryFlushWorker:
    """Background flush worker for memory records."""

    def __init__(
        self,
        *,
        workspace_root: str,
        repository: MemoryRepository,
        max_batch_size: int,
    ) -> None:
        self._workspace_root = workspace_root
        self._repository = repository
        self._max_batch_size = max_batch_size
        self._queue: queue.Queue[_FlushItem | _FlushBarrier | None] = queue.Queue()
        self._thread = threading.Thread(
            target=self._run,
            name="inty-v2-memory-flush",
            daemon=True,
        )
        self._thread.start()

    def enqueue(self, record: MemoryRecord) -> None:
        self._queue.put(_FlushItem(record=record))

    def flush_now(self, *, timeout_s: float) -> None:
        done = threading.Event()
        self._queue.put(_FlushBarrier(done=done))
        if not done.wait(timeout=timeout_s):
            raise TimeoutError(
                f"memory flush barrier timed out after {timeout_s:.1f}s"
            )

    def shutdown(self, *, timeout_s: float) -> None:
        self.flush_now(timeout_s=timeout_s)
        self._queue.put(None)
        self._thread.join(timeout=timeout_s)
        if self._thread.is_alive():
            raise TimeoutError(
                f"memory flush worker did not stop after {timeout_s:.1f}s"
            )

    def _run(self) -> None:
        while True:
            item = self._queue.get()
            if item is None:
                self._queue.task_done()
                return
            if isinstance(item, _FlushBarrier):
                item.done.set()
                self._queue.task_done()
                continue

            batch: list[MemoryRecord] = [item.record]
            barriers: list[_FlushBarrier] = []
            for _ in range(self._max_batch_size - 1):
                try:
                    nxt = self._queue.get_nowait()
                except queue.Empty:
                    break
                if nxt is None:
                    # Put it back for the outer loop to consume and stop.
                    self._queue.put(None)
                    self._queue.task_done()
                    break
                if isinstance(nxt, _FlushBarrier):
                    barriers.append(nxt)
                    self._queue.task_done()
                    break
                batch.append(nxt.record)
                self._queue.task_done()

            for rec in batch:
                self._repository.upsert_document(
                    workspace_root=self._workspace_root,
                    record=rec,
                )
            logger.debug(
                "memory.flush batch_done ws={} batch_n={} latest={}",
                self._workspace_root,
                len(batch),
                batch[-1].relative_path,
            )
            for bar in barriers:
                bar.done.set()
            self._queue.task_done()


class MemoryStore:
    """Cache-first memory store with async repository flush and optional file mirror."""

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
        self._flush_worker = (
            MemoryFlushWorker(
                workspace_root=self._workspace_root_str,
                repository=repository,
                max_batch_size=flush_batch_size,
            )
            if repository is not None
            else None
        )

    def _persisted_version(self, relative_path: str) -> int:
        if self._repository is None:
            return 0
        return self._repository.max_version(
            workspace_root=self._workspace_root_str,
            relative_path=relative_path,
        )

    def _normalize_relative_path(self, relative_path: str) -> str:
        rel = (relative_path or "").strip().replace("\\", "/")
        if not rel:
            raise ValueError("relative_path must be non-empty")
        if rel.startswith("/"):
            raise ValueError("relative_path must be workspace-relative")
        abs_path = (self._workspace_root / rel).resolve()
        return abs_path.relative_to(self._workspace_root).as_posix()

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
                loaded = self._cache.put(
                    relative_path=rel,
                    content=rec.content,
                    version=rec.version,
                    updated_at=rec.updated_at,
                )
                self._mirror.write(record=loaded)
                return loaded.content

        mirrored = self._mirror.read_if_exists(relative_path=rel)
        if mirrored is None:
            return None
        self._cache.put(
            relative_path=rel,
            content=mirrored,
            version=0,
            updated_at=utc_iso_ts(),
        )
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
        cached = self._cache.get(rel)
        if cached is None:
            persisted = self._persisted_version(rel)
            if persisted > 0:
                self._cache.put(
                    relative_path=rel,
                    content=content,
                    version=persisted,
                    updated_at=utc_iso_ts(),
                )
        rec = self._cache.write(relative_path=rel, content=content)
        self._mirror.write(record=rec)
        if self._flush_worker is not None:
            self._flush_worker.enqueue(rec)

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
        if self._flush_worker is None:
            return
        self._flush_worker.flush_now(timeout_s=timeout_s)

    def shutdown(self, *, timeout_s: float = 5.0) -> None:
        if self._flush_worker is None:
            return
        self._flush_worker.shutdown(timeout_s=timeout_s)
