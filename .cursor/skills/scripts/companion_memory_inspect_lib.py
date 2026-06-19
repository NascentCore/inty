"""Shared helpers for companion MemoryStore inspect CLI scripts.

Generated entirely by Cursor agent for debugging companion MemoryDoc state in Postgres.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.companion_harness.companion.scope import CompanionScope
    from app.core.companion_harness.memory.memory_store import MemoryStore


@dataclass(frozen=True)
class DocumentVersionRow:
    """Latest or historical MemoryDoc version metadata plus body."""

    relative_path: str
    sequence_id: int
    record_uuid: str
    created_at: str
    content: str

    @property
    def content_chars(self) -> int:
        return len(self.content)


def repo_root_from_cwd() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "app" / "models").is_dir():
        return cwd
    raise SystemExit(
        "Run from inty repo root (need app/models/ on PYTHONPATH). "
        "Example: PYTHONPATH=. python .cursor/skills/scripts/<script>.py ..."
    )


def resolve_inty_config_yaml_path(config_override: str | None) -> Path:
    """Resolve config path like ``app.core.config`` (``INTY_CONFIG_YAML`` or local yaml).

    Precedence: explicit ``--config`` / CLI override, then ``INTY_CONFIG_YAML`` env,
    then ``devops/config.yaml.local``. Always writes the resolved path back to
    ``INTY_CONFIG_YAML`` before any ``app.*`` import.

    TODO(INTY_CONFIG_YAML): move to app.utils.config — https://github.com/NascentCore/inty/issues/3530
    """
    root = repo_root_from_cwd()
    raw = (
        config_override
        or os.environ.get("INTY_CONFIG_YAML")
        or "devops/config.yaml.local"
    ).strip()
    if not raw:
        raise SystemExit("Config path is empty")
    config_path = Path(raw)
    if not config_path.is_absolute():
        config_path = (root / config_path).resolve()
    if not config_path.is_file():
        raise SystemExit(f"Config file not found: {config_path}")
    os.environ["INTY_CONFIG_YAML"] = str(config_path)
    return config_path


def apply_inty_config_env(config_override: str | None) -> Path:
    """Bootstrap Inty YAML config via ``INTY_CONFIG_YAML`` (see ``resolve_inty_config_yaml_path``)."""
    return resolve_inty_config_yaml_path(config_override)


def load_database_dsn() -> str:
    from app.core.config import global_config_loaded_from_config_yaml

    dsn = (global_config_loaded_from_config_yaml.database.url or "").strip()
    if not dsn:
        raise SystemExit("database.url is empty in config")
    return dsn


def list_agent_scopes(agent_id: str) -> list[CompanionScope]:
    assert agent_id
    from sqlalchemy import select

    from app.core.companion_harness.companion.scope import CompanionScope
    from app.db.base import SessionLocal
    from app.models.companion_memory_documents import CompanionMemoryDocumentVersion

    with SessionLocal() as session:
        stmt = (
            select(
                CompanionMemoryDocumentVersion.user_id,
                CompanionMemoryDocumentVersion.chat_id,
            )
            .where(CompanionMemoryDocumentVersion.companion_id == agent_id)
            .distinct()
            .order_by(
                CompanionMemoryDocumentVersion.user_id,
                CompanionMemoryDocumentVersion.chat_id,
            )
        )
        rows = session.execute(stmt).all()
    scopes: list[CompanionScope] = []
    for user_id, chat_id in rows:
        uid = str(user_id or "").strip()
        cid = str(chat_id or "").strip()
        if not uid or not cid:
            continue
        scopes.append(
            CompanionScope(
                user_id=uid,
                companion_id=agent_id,
                chat_id=cid,
            )
        )
    return scopes


def list_companion_scopes(companion_id: str) -> list[CompanionScope]:
    """Alias for ``list_agent_scopes`` (ORM column is ``companion_id``)."""
    return list_agent_scopes(companion_id)


def print_scope_candidates(scopes: list[CompanionScope]) -> None:
    sys.stdout.write("Multiple MemoryStore scopes; pass --user-id and --chat-id:\n")
    for scope in scopes:
        sys.stdout.write(
            f"  user_id={scope.user_id!r} chat_id={scope.chat_id!r}\n"
        )


def resolve_scope(
    *,
    agent_id: str,
    user_id: str,
    chat_id: str,
) -> CompanionScope:
    assert agent_id
    scopes = list_agent_scopes(agent_id)
    if not scopes:
        raise SystemExit(f"No MemoryStore rows for agent_id={agent_id!r}")

    if user_id and chat_id:
        for scope in scopes:
            if scope.user_id == user_id and scope.chat_id == chat_id:
                return scope
        raise SystemExit(
            f"No MemoryStore scope for agent_id={agent_id!r} "
            f"user_id={user_id!r} chat_id={chat_id!r}"
        )

    if len(scopes) == 1:
        return scopes[0]

    print_scope_candidates(scopes)
    raise SystemExit(2)


def open_memory_store(scope: CompanionScope, *, dsn: str) -> MemoryStore:
    from app.core.companion_harness.memory.memory_registry import get_memory_store

    return get_memory_store(scope, dsn=dsn)


def _scope_filters(scope: CompanionScope, kind_value: str, cal: date | None):
    from sqlalchemy import and_

    from app.models.companion_memory_documents import CompanionMemoryDocumentVersion

    filters = [
        CompanionMemoryDocumentVersion.user_id == scope.user_id,
        CompanionMemoryDocumentVersion.companion_id == scope.companion_id,
        CompanionMemoryDocumentVersion.chat_id == scope.chat_id,
        CompanionMemoryDocumentVersion.document_kind == kind_value,
    ]
    if cal is None:
        filters.append(CompanionMemoryDocumentVersion.calendar_date.is_(None))
    else:
        filters.append(CompanionMemoryDocumentVersion.calendar_date == cal)
    return and_(*filters)


def fetch_document_versions(
    scope: CompanionScope,
    relative_path: str,
    *,
    limit: int,
) -> list[DocumentVersionRow]:
    assert limit >= 1
    from sqlalchemy import select

    from app.core.companion_harness.memory.memory_store_document_mapping import (
        parse_memory_store_relative_path,
    )
    from app.db.base import SessionLocal
    from app.models.companion_memory_documents import CompanionMemoryDocumentVersion

    try:
        kind, cal = parse_memory_store_relative_path(relative_path)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    stmt = (
        select(CompanionMemoryDocumentVersion)
        .where(_scope_filters(scope, kind.value, cal))
        .order_by(CompanionMemoryDocumentVersion.sequence_id.desc())
        .limit(limit)
    )
    with SessionLocal() as session:
        rows = list(session.scalars(stmt).all())
    out: list[DocumentVersionRow] = []
    for row in rows:
        created_at = row.created_at.isoformat() if row.created_at else ""
        out.append(
            DocumentVersionRow(
                relative_path=relative_path,
                sequence_id=int(row.sequence_id),
                record_uuid=str(row.record_uuid),
                created_at=created_at,
                content=str(row.content),
            )
        )
    return out


def list_latest_document_kinds(scope: CompanionScope) -> list[DocumentVersionRow]:
    """One latest row per (document_kind, calendar_date) in the scope."""
    from sqlalchemy import func, select

    from app.core.companion_harness.memory.memory_store_document_mapping import (
        CompanionMemoryDocumentKind,
        relative_path_for_kind,
    )
    from app.db.base import SessionLocal
    from app.models.companion_memory_documents import CompanionMemoryDocumentVersion

    latest_seq = (
        select(
            CompanionMemoryDocumentVersion.document_kind.label("document_kind"),
            CompanionMemoryDocumentVersion.calendar_date.label("calendar_date"),
            func.max(CompanionMemoryDocumentVersion.sequence_id).label("max_seq"),
        )
        .where(
            CompanionMemoryDocumentVersion.user_id == scope.user_id,
            CompanionMemoryDocumentVersion.companion_id == scope.companion_id,
            CompanionMemoryDocumentVersion.chat_id == scope.chat_id,
        )
        .group_by(
            CompanionMemoryDocumentVersion.document_kind,
            CompanionMemoryDocumentVersion.calendar_date,
        )
        .subquery()
    )
    stmt = (
        select(CompanionMemoryDocumentVersion)
        .join(
            latest_seq,
            (
                CompanionMemoryDocumentVersion.document_kind
                == latest_seq.c.document_kind
            )
            & (
                CompanionMemoryDocumentVersion.calendar_date.is_not_distinct_from(
                    latest_seq.c.calendar_date
                )
            )
            & (
                CompanionMemoryDocumentVersion.sequence_id == latest_seq.c.max_seq
            ),
        )
        .where(
            CompanionMemoryDocumentVersion.user_id == scope.user_id,
            CompanionMemoryDocumentVersion.companion_id == scope.companion_id,
            CompanionMemoryDocumentVersion.chat_id == scope.chat_id,
        )
        .order_by(
            CompanionMemoryDocumentVersion.document_kind,
            CompanionMemoryDocumentVersion.calendar_date,
        )
    )
    with SessionLocal() as session:
        rows = list(session.scalars(stmt).all())
    out: list[DocumentVersionRow] = []
    for row in rows:
        try:
            kind = CompanionMemoryDocumentKind(str(row.document_kind))
            rel = relative_path_for_kind(kind, row.calendar_date)
        except ValueError:
            rel = f"<unknown:{row.document_kind}>"
        created_at = row.created_at.isoformat() if row.created_at else ""
        out.append(
            DocumentVersionRow(
                relative_path=rel,
                sequence_id=int(row.sequence_id),
                record_uuid=str(row.record_uuid),
                created_at=created_at,
                content=str(row.content),
            )
        )
    return out


def iter_scope_documents_via_memory_store(
    store: MemoryStore,
) -> list[tuple[str, str | None]]:
    """Return (relative_path, content) for every path known to MemoryStore."""
    paths = store.iter_stored_relative_paths()
    out: list[tuple[str, str | None]] = []
    for rel in paths:
        out.append((rel, store.read_document_if_exists(rel)))
    return out
