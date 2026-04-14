"""Memory store: DB-authoritative append-only versions; in-memory only when no repository."""

from __future__ import annotations

import json
import threading
import uuid as uuid_mod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .utc import utc_iso_ts
from .workspace_doc_mapping import (
    CompanionWorkspaceDocKind,
    parse_workspace_relative_path,
    relative_path_for_kind,
)


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

    def list_all_relative_paths(self, *, workspace_root: str) -> list[str]: ...


class SqlAlchemyMemoryRepository:
    """Append-only companion workspace documents via SQLAlchemy ORM."""

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
        from app.models.companion_workspace import CompanionWorkspaceDocumentVersion

        return sql_and, sql_select, SessionLocal, CompanionWorkspaceDocumentVersion

    def read_document(
        self,
        *,
        workspace_root: str,
        relative_path: str,
    ) -> MemoryRecord | None:
        sql_and, sql_select, SessionLocal, CompanionWorkspaceDocumentVersion = (
            self._orm()
        )
        _ = workspace_root
        kind, cal = parse_workspace_relative_path(relative_path)
        filters = [
            sql_and(
                CompanionWorkspaceDocumentVersion.user_id == self._user_id,
                CompanionWorkspaceDocumentVersion.companion_id == self._companion_id,
                CompanionWorkspaceDocumentVersion.chat_id == self._chat_id,
            ),
            CompanionWorkspaceDocumentVersion.document_kind == kind.value,
        ]
        if cal is None:
            filters.append(CompanionWorkspaceDocumentVersion.calendar_date.is_(None))
        else:
            filters.append(CompanionWorkspaceDocumentVersion.calendar_date == cal)
        stmt = (
            sql_select(CompanionWorkspaceDocumentVersion)
            .where(sql_and(*filters))
            .order_by(CompanionWorkspaceDocumentVersion.sequence_id.desc())
            .limit(1)
        )
        with SessionLocal() as session:
            row = session.scalars(stmt).first()
        if row is None:
            return None
        created_at = row.created_at.isoformat() if row.created_at else ""
        return MemoryRecord(
            record_uuid=str(row.record_uuid),
            sequence_id=int(row.sequence_id),
            relative_path=relative_path,
            content=str(row.content),
            created_at=created_at,
        )

    def list_all_relative_paths(self, *, workspace_root: str) -> list[str]:
        sql_and, sql_select, SessionLocal, CompanionWorkspaceDocumentVersion = (
            self._orm()
        )
        _ = workspace_root
        stmt = (
            sql_select(
                CompanionWorkspaceDocumentVersion.document_kind,
                CompanionWorkspaceDocumentVersion.calendar_date,
            )
            .where(
                sql_and(
                    CompanionWorkspaceDocumentVersion.user_id == self._user_id,
                    CompanionWorkspaceDocumentVersion.companion_id
                    == self._companion_id,
                    CompanionWorkspaceDocumentVersion.chat_id == self._chat_id,
                )
            )
            .distinct()
        )
        with SessionLocal() as session:
            pairs = list(session.execute(stmt).all())
        out: list[str] = []
        for kind_val, cal in pairs:
            kind = CompanionWorkspaceDocKind(kind_val)
            out.append(relative_path_for_kind(kind, cal))
        return sorted(out)

    def append_document(
        self,
        *,
        workspace_root: str,
        relative_path: str,
        content: str,
        record_uuid: str,
    ) -> MemoryRecord:
        _, _, SessionLocal, CompanionWorkspaceDocumentVersion = self._orm()
        _ = workspace_root
        kind, cal = parse_workspace_relative_path(relative_path)
        row = CompanionWorkspaceDocumentVersion(
            record_uuid=record_uuid,
            user_id=self._user_id,
            companion_id=self._companion_id,
            chat_id=self._chat_id,
            document_kind=kind.value,
            calendar_date=cal,
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

    def relative_paths(self) -> list[str]:
        with self._lock:
            return sorted(self._records.keys())


class MemoryStore:
    """Repository-backed or in-process-only memory store (never reads user workspace files)."""

    def __init__(
        self,
        *,
        workspace_root: Path,
        repository: MemoryRepository | None,
        flush_batch_size: int = 64,
    ) -> None:
        self._workspace_root = workspace_root.resolve()
        self._workspace_root_str = str(self._workspace_root)
        self._cache = MemoryCache()
        self._repository = repository
        _ = flush_batch_size

    @property
    def uses_repository_without_workspace_disk(self) -> bool:
        return self._repository is not None

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
        return 1

    def iter_stored_relative_paths(self) -> list[str]:
        repo = self._repository
        if repo is not None:
            list_fn = getattr(repo, "list_all_relative_paths", None)
            if callable(list_fn):
                return list(list_fn(workspace_root=self._workspace_root_str))
        return self._cache.relative_paths()

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
                return loaded.content
        return None

    def read_document(self, relative_path: str) -> str:
        body = self.read_document_if_exists(relative_path)
        if body is None:
            raise FileNotFoundError(
                f"memory document not found: {self._workspace_root / relative_path}"
            )
        return body

    def write_document(self, relative_path: str, content: str) -> None:
        rel = self._normalize_relative_path(relative_path)
        new_record_uuid = str(uuid_mod.uuid4())
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
        self.write_document(rel, merged)

    def flush_now(self, *, timeout_s: float = 5.0) -> None:
        return

    def shutdown(self, *, timeout_s: float = 5.0) -> None:
        return
