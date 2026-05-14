"""Memory store: DB append-only rows; snapshot replaces body, suffix concatenates (line/jsonl)."""

from __future__ import annotations

import json
import threading
import uuid as uuid_mod
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Literal, Protocol

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.utc import utc_iso_ts

from .memory_store_document_mapping import (
    CompanionMemoryDocumentKind,
    parse_memory_store_relative_path,
    relative_path_for_kind,
)


def normalize_memory_store_relative_path(relative_path: str) -> str:
    """Normalize a scope-relative posix path without touching the host filesystem.

    Rejects empty paths, absolute paths, and ``..`` segments that would escape the root.
    """
    rel = (relative_path or "").strip().replace("\\", "/")
    if not rel:
        raise ValueError("relative_path must be non-empty")
    if rel.startswith("/"):
        raise ValueError("relative_path must be scope-root-relative")
    parts: list[str] = []
    for part in PurePosixPath(rel).parts:
        if part == "..":
            if not parts:
                raise ValueError("relative_path escapes scope root")
            parts.pop()
        elif part in (".", ""):
            continue
        else:
            parts.append(part)
    if not parts:
        raise ValueError("relative_path must be non-empty")
    return "/".join(parts)


_CONTENT_MODE_SNAPSHOT: Literal["snapshot"] = "snapshot"
_CONTENT_MODE_SUFFIX: Literal["suffix"] = "suffix"


def _fold_versioned_contents(rows: list[tuple[str, str]]) -> str:
    """Build one logical document body from DB rows in ``sequence_id`` order."""
    body = ""
    for mode, chunk in rows:
        if mode == _CONTENT_MODE_SUFFIX:
            body += chunk
        else:
            body = chunk
    return body


@dataclass(frozen=True)
class MemoryRecord:
    record_uuid: str
    sequence_id: int
    relative_path: str
    content: str
    created_at: str


class MemoryRepository(Protocol):
    def read_document(self, *, relative_path: str) -> MemoryRecord | None: ...

    def append_document(
        self,
        *,
        relative_path: str,
        content: str,
        record_uuid: str,
        content_mode: Literal["snapshot", "suffix"] = "snapshot",
    ) -> MemoryRecord: ...

    def list_all_relative_paths(self) -> list[str]: ...


class SqlAlchemyMemoryRepository:
    """Append-only MemoryStore documents via SQLAlchemy ORM."""

    def __init__(
        self,
        *,
        user_id: str,
        companion_id: str,
        chat_id: str,
    ) -> None:
        self._user_id = user_id
        self._companion_id = companion_id
        self._chat_id = chat_id

    def _orm(self):
        from sqlalchemy import and_ as sql_and
        from sqlalchemy import select as sql_select

        from app.db.base import SessionLocal
        from app.models.companion_memory_documents import CompanionMemoryDocumentVersion

        return sql_and, sql_select, SessionLocal, CompanionMemoryDocumentVersion

    def read_document(self, *, relative_path: str) -> MemoryRecord | None:
        sql_and, sql_select, SessionLocal, CompanionMemoryDocumentVersion = self._orm()
        kind, cal = parse_memory_store_relative_path(relative_path)
        filters = [
            sql_and(
                CompanionMemoryDocumentVersion.user_id == self._user_id,
                CompanionMemoryDocumentVersion.companion_id == self._companion_id,
                CompanionMemoryDocumentVersion.chat_id == self._chat_id,
            ),
            CompanionMemoryDocumentVersion.document_kind == kind.value,
        ]
        if cal is None:
            filters.append(CompanionMemoryDocumentVersion.calendar_date.is_(None))
        else:
            filters.append(CompanionMemoryDocumentVersion.calendar_date == cal)
        stmt = (
            sql_select(CompanionMemoryDocumentVersion)
            .where(sql_and(*filters))
            .order_by(CompanionMemoryDocumentVersion.sequence_id.asc())
        )
        with SessionLocal() as session:
            orm_rows = list(session.scalars(stmt).all())
        if not orm_rows:
            return None
        last = orm_rows[-1]
        pairs: list[tuple[str, str]] = []
        for r in orm_rows:
            mode = getattr(r, "content_mode", None) or _CONTENT_MODE_SNAPSHOT
            if mode not in (_CONTENT_MODE_SNAPSHOT, _CONTENT_MODE_SUFFIX):
                mode = _CONTENT_MODE_SNAPSHOT
            pairs.append((mode, str(r.content)))
        folded = _fold_versioned_contents(pairs)
        created_at = last.created_at.isoformat() if last.created_at else ""
        return MemoryRecord(
            record_uuid=str(last.record_uuid),
            sequence_id=int(last.sequence_id),
            relative_path=relative_path,
            content=folded,
            created_at=created_at,
        )

    def list_all_relative_paths(self) -> list[str]:
        sql_and, sql_select, SessionLocal, CompanionMemoryDocumentVersion = self._orm()
        stmt = (
            sql_select(
                CompanionMemoryDocumentVersion.document_kind,
                CompanionMemoryDocumentVersion.calendar_date,
            )
            .where(
                sql_and(
                    CompanionMemoryDocumentVersion.user_id == self._user_id,
                    CompanionMemoryDocumentVersion.companion_id == self._companion_id,
                    CompanionMemoryDocumentVersion.chat_id == self._chat_id,
                )
            )
            .distinct()
        )
        with SessionLocal() as session:
            pairs = list(session.execute(stmt).all())
        out: list[str] = []
        for kind_val, cal in pairs:
            try:
                kind = CompanionMemoryDocumentKind(kind_val)
            except ValueError:
                continue
            try:
                out.append(relative_path_for_kind(kind, cal))
            except ValueError:
                continue
        return sorted(out)

    def append_document(
        self,
        *,
        relative_path: str,
        content: str,
        record_uuid: str,
        content_mode: Literal["snapshot", "suffix"] = "snapshot",
    ) -> MemoryRecord:
        _, _, SessionLocal, CompanionMemoryDocumentVersion = self._orm()
        if content_mode not in (_CONTENT_MODE_SNAPSHOT, _CONTENT_MODE_SUFFIX):
            raise ValueError(f"invalid content_mode: {content_mode!r}")
        kind, cal = parse_memory_store_relative_path(relative_path)
        row = CompanionMemoryDocumentVersion(
            record_uuid=record_uuid,
            user_id=self._user_id,
            companion_id=self._companion_id,
            chat_id=self._chat_id,
            document_kind=kind.value,
            calendar_date=cal,
            content_mode=content_mode,
            content=content,
        )
        with SessionLocal() as session:
            session.add(row)
            session.commit()
            session.refresh(row)
        created_at = row.created_at.isoformat() if row.created_at else ""
        return MemoryRecord(
            record_uuid=record_uuid,
            sequence_id=int(row.sequence_id),
            relative_path=relative_path,
            content=content,
            created_at=created_at,
        )


class MemoryCache:
    """Thread-safe in-memory snapshot for one MemoryStore scope."""

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

    def relative_paths(self) -> list[str]:
        with self._lock:
            return sorted(self._records.keys())


class MemoryStore:
    """Repository-backed or in-process-only store (never reads host filesystem as authority)."""

    def __init__(
        self,
        *,
        scope: CompanionScope,
        repository: MemoryRepository | None,
        flush_batch_size: int = 64,
    ) -> None:
        self._scope = scope
        self._cache = MemoryCache()
        self._repository = repository
        _ = flush_batch_size

    @property
    def scope(self) -> CompanionScope:
        return self._scope

    @property
    def uses_repository_without_scope_disk(self) -> bool:
        return self._repository is not None

    def _normalize_relative_path(self, relative_path: str) -> str:
        return normalize_memory_store_relative_path(relative_path)

    def _next_local_sequence(self, relative_path: str) -> int:
        cur = self._cache.get(relative_path)
        if cur is not None:
            return cur.sequence_id + 1
        return 1

    def iter_stored_relative_paths(self) -> list[str]:
        repo = self._repository
        if repo is not None:
            list_fn = getattr(repo, "list_all_relative_paths", None)
            if callable(list_fn):
                return list(list_fn())
        return self._cache.relative_paths()

    def read_document_if_exists(self, relative_path: str) -> str | None:
        rel = self._normalize_relative_path(relative_path)
        cached = self._cache.get(rel)
        if cached is not None:
            return cached.content

        if self._repository is not None:
            rec = self._repository.read_document(relative_path=rel)
            if rec is not None:
                loaded = self._cache.put_committed(rec)
                return loaded.content
        return None

    def read_document(self, relative_path: str) -> str:
        body = self.read_document_if_exists(relative_path)
        if body is None:
            rel = self._normalize_relative_path(relative_path)
            raise FileNotFoundError(
                f"memory document not found: scope={self._scope.registry_key()} path={rel!r}"
            )
        return body

    def write_document(self, relative_path: str, content: str) -> None:
        rel = self._normalize_relative_path(relative_path)
        new_record_uuid = str(uuid_mod.uuid4())
        if self._repository is not None:
            committed = self._repository.append_document(
                relative_path=rel,
                content=content,
                record_uuid=new_record_uuid,
                content_mode=_CONTENT_MODE_SNAPSHOT,
            )
        else:
            committed = MemoryRecord(
                record_uuid=new_record_uuid,
                sequence_id=self._next_local_sequence(rel),
                relative_path=rel,
                content=content,
                created_at=utc_iso_ts(),
            )
        self._cache.put_committed(committed)

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
        if self._repository is not None:
            fragment = merged[len(cur) :]
            new_record_uuid = str(uuid_mod.uuid4())
            committed = self._repository.append_document(
                relative_path=rel,
                content=fragment,
                record_uuid=new_record_uuid,
                content_mode=_CONTENT_MODE_SUFFIX,
            )
            self._cache.put_committed(
                MemoryRecord(
                    record_uuid=committed.record_uuid,
                    sequence_id=committed.sequence_id,
                    relative_path=rel,
                    content=merged,
                    created_at=committed.created_at,
                )
            )
        else:
            self.write_document(rel, merged)

    def append_jsonl_record(self, relative_path: str, record: dict[str, Any]) -> None:
        rel = self._normalize_relative_path(relative_path)
        line = json.dumps(record, ensure_ascii=False)
        cur = self.read_document_if_exists(rel)
        if cur is None:
            cur = ""
        merged = cur
        if merged and not merged.endswith("\n"):
            merged += "\n"
        merged += line + "\n"
        if self._repository is not None:
            fragment = merged[len(cur) :]
            new_record_uuid = str(uuid_mod.uuid4())
            committed = self._repository.append_document(
                relative_path=rel,
                content=fragment,
                record_uuid=new_record_uuid,
                content_mode=_CONTENT_MODE_SUFFIX,
            )
            self._cache.put_committed(
                MemoryRecord(
                    record_uuid=committed.record_uuid,
                    sequence_id=committed.sequence_id,
                    relative_path=rel,
                    content=merged,
                    created_at=committed.created_at,
                )
            )
        else:
            self.write_document(rel, merged)

    def flush_now(self, *, timeout_s: float = 5.0) -> None:
        return

    def shutdown(self, *, timeout_s: float = 5.0) -> None:
        return
