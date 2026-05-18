#!/usr/bin/env python3
"""Print latest MemoryStore document body from companion_memory_document_versions.

Companion harness inspect helper (``.cursor/skills/inspect-companion-harness/SKILL.md``).
Resolves document paths via ``parse_memory_store_relative_path`` (e.g. STYLE.md → style).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Any

import cyclopts
import yaml
from sqlalchemy import create_engine, text

from app.core.companion_harness.memory.memory_store_document_mapping import (
    CompanionMemoryDocumentKind,
    all_static_relative_paths,
    parse_memory_store_relative_path,
    relative_path_for_kind,
)
from app.utils.config import DatabaseSettings

_TABLE = "companion_memory_document_versions"


@dataclass(frozen=True)
class ScopeRow:
    user_id: str
    chat_id: str


@dataclass(frozen=True)
class VersionRow:
    sequence_id: int
    created_at: datetime
    content: str
    calendar_date: date | None


def _load_database_settings(config_path: Path) -> DatabaseSettings:
    if not config_path.is_file():
        raise SystemExit(f"config not found: {config_path}")
    raw = yaml.safe_load(config_path.read_text())
    if not isinstance(raw, dict):
        raise SystemExit(f"config root must be a mapping: {config_path}")
    block = raw.get("database")
    if not isinstance(block, dict):
        raise SystemExit(f"config missing database block: {config_path}")
    return DatabaseSettings.model_validate(block)


def _resolve_document(relative_path: str) -> tuple[CompanionMemoryDocumentKind, date | None]:
    rel = relative_path.strip().replace("\\", "/")
    if not rel.endswith(".md") and not rel.endswith(".json") and not rel.endswith(".jsonl"):
        if rel.upper() == rel and "." not in rel:
            rel = f"{rel}.md"
    try:
        return parse_memory_store_relative_path(rel)
    except ValueError as exc:
        static = ", ".join(sorted(all_static_relative_paths()))
        raise SystemExit(
            f"unsupported document path {relative_path!r}: {exc}\n"
            f"static paths include: {static}\n"
            "dated paths: memory/daily/YYYY-MM-DD.md, memory/YYYY-MM-DD.md"
        ) from exc


def _list_scopes(engine: Any, companion_id: str) -> list[ScopeRow]:
    sql = text(
        f"""
        SELECT DISTINCT user_id, chat_id
        FROM {_TABLE}
        WHERE companion_id = :companion_id
        ORDER BY user_id, chat_id
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"companion_id": companion_id}).fetchall()
    return [ScopeRow(user_id=str(r[0]), chat_id=str(r[1])) for r in rows]


def _pick_scope(
    scopes: list[ScopeRow],
    companion_id: str,
    user_id: str,
    chat_id: str,
) -> ScopeRow:
    if not scopes:
        raise SystemExit(f"no memory versions for companion_id={companion_id}")
    if user_id and chat_id:
        for s in scopes:
            if s.user_id == user_id and s.chat_id == chat_id:
                return s
        raise SystemExit(
            f"no rows for user_id={user_id!r} chat_id={chat_id!r} "
            f"companion_id={companion_id!r}"
        )
    if user_id and not chat_id:
        matched = [s for s in scopes if s.user_id == user_id]
        if len(matched) == 1:
            return matched[0]
        if not matched:
            raise SystemExit(f"no chat_id for user_id={user_id!r} companion_id={companion_id!r}")
        _print_scopes(companion_id, matched)
        raise SystemExit("multiple chat_id for user_id; pass --chat-id")
    if chat_id and not user_id:
        matched = [s for s in scopes if s.chat_id == chat_id]
        if len(matched) == 1:
            return matched[0]
        if not matched:
            raise SystemExit(f"no user_id for chat_id={chat_id!r} companion_id={companion_id!r}")
        _print_scopes(companion_id, matched)
        raise SystemExit("multiple user_id for chat_id; pass --user-id")
    if len(scopes) == 1:
        return scopes[0]
    _print_scopes(companion_id, scopes)
    raise SystemExit("multiple scopes; pass --user-id and --chat-id")


def _print_scopes(companion_id: str, scopes: list[ScopeRow]) -> None:
    print(f"companion_id={companion_id} scopes ({len(scopes)}):", file=sys.stderr)
    for s in scopes:
        print(f"  user_id={s.user_id} chat_id={s.chat_id}", file=sys.stderr)


def _fetch_versions(
    engine: Any,
    scope: ScopeRow,
    companion_id: str,
    document_kind: CompanionMemoryDocumentKind,
    calendar_date: date | None,
    limit: int,
) -> list[VersionRow]:
    if calendar_date is None:
        date_clause = "calendar_date IS NULL"
        params: dict[str, Any] = {
            "user_id": scope.user_id,
            "companion_id": companion_id,
            "chat_id": scope.chat_id,
            "document_kind": document_kind.value,
            "limit": limit,
        }
    else:
        date_clause = "calendar_date = :calendar_date"
        params = {
            "user_id": scope.user_id,
            "companion_id": companion_id,
            "chat_id": scope.chat_id,
            "document_kind": document_kind.value,
            "calendar_date": calendar_date,
            "limit": limit,
        }
    sql = text(
        f"""
        SELECT sequence_id, created_at, content, calendar_date
        FROM {_TABLE}
        WHERE user_id = :user_id
          AND companion_id = :companion_id
          AND chat_id = :chat_id
          AND document_kind = :document_kind
          AND {date_clause}
        ORDER BY sequence_id DESC
        LIMIT :limit
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    out: list[VersionRow] = []
    for r in rows:
        out.append(
            VersionRow(
                sequence_id=int(r[0]),
                created_at=r[1],
                content=str(r[2]),
                calendar_date=r[3],
            )
        )
    return out


def _list_kind_summary(
    engine: Any,
    scope: ScopeRow,
    companion_id: str,
) -> None:
    sql = text(
        f"""
        SELECT document_kind,
               MAX(sequence_id) AS max_seq,
               MAX(created_at) AS last_at,
               COUNT(*) AS version_count
        FROM {_TABLE}
        WHERE user_id = :user_id
          AND companion_id = :companion_id
          AND chat_id = :chat_id
        GROUP BY document_kind
        ORDER BY document_kind
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(
            sql,
            {
                "user_id": scope.user_id,
                "companion_id": companion_id,
                "chat_id": scope.chat_id,
            },
        ).fetchall()
    print(
        f"scope user_id={scope.user_id} companion_id={companion_id} chat_id={scope.chat_id}"
    )
    if not rows:
        print("(no rows)")
        return
    for r in rows:
        print(
            f"{r[0]:32} max_seq={r[1]} last_at={r[2]} versions={r[3]}",
        )


def main(
    document: Annotated[
        str,
        cyclopts.Parameter(
            help="Logical path, e.g. STYLE.md, context.json, memory/daily/2026-05-18.md"
        ),
    ],
    companion_id: Annotated[
        str,
        cyclopts.Parameter(help="agent_id / MemoryStore companion_id (UUID)"),
    ],
    user_id: Annotated[
        str,
        cyclopts.Parameter(help="Scope user_id; omit when exactly one scope exists"),
    ] = "",
    chat_id: Annotated[
        str,
        cyclopts.Parameter(help="Scope chat_id; omit when exactly one scope exists"),
    ] = "",
    config: Annotated[
        str,
        cyclopts.Parameter(help="Repo config YAML with database block"),
    ] = "config.yaml",
    limit: Annotated[
        int,
        cyclopts.Parameter(help="How many recent versions to print (newest first)"),
    ] = 1,
    meta_only: Annotated[
        bool,
        cyclopts.Parameter(name="--meta-only", help="Print metadata only, not content body"),
    ] = False,
    list_scopes: Annotated[
        bool,
        cyclopts.Parameter(
            name="--list-scopes",
            help="List distinct (user_id, chat_id) for companion_id and exit",
        ),
    ] = False,
    list_kinds: Annotated[
        bool,
        cyclopts.Parameter(
            name="--list-kinds",
            help="Summarize document_kind rows for resolved scope and exit",
        ),
    ] = False,
) -> None:
    assert limit >= 1
    cfg_path = Path(config)
    db = _load_database_settings(cfg_path)
    engine = create_engine(
        db.url.replace("postgresql://", "postgresql+psycopg2://", 1),
        pool_pre_ping=True,
    )

    scopes = _list_scopes(engine, companion_id)
    if list_scopes:
        _print_scopes(companion_id, scopes)
        return

    scope = _pick_scope(scopes, companion_id, user_id.strip(), chat_id.strip())

    if list_kinds:
        _list_kind_summary(engine, scope, companion_id)
        return

    kind, calendar_date = _resolve_document(document)
    canonical = relative_path_for_kind(kind, calendar_date)
    versions = _fetch_versions(engine, scope, companion_id, kind, calendar_date, limit)
    if not versions:
        raise SystemExit(
            f"no version for {canonical!r} "
            f"user_id={scope.user_id} chat_id={scope.chat_id} companion_id={companion_id}"
        )

    for i, ver in enumerate(versions):
        if i > 0:
            print("---")
        print(
            f"# {canonical}  sequence_id={ver.sequence_id}  created_at={ver.created_at}"
        )
        print(
            f"# scope user_id={scope.user_id} chat_id={scope.chat_id} "
            f"companion_id={companion_id}  chars={len(ver.content)}"
        )
        if meta_only:
            continue
        sys.stdout.write(ver.content)
        if ver.content and not ver.content.endswith("\n"):
            sys.stdout.write("\n")


if __name__ == "__main__":
    cyclopts.run(main)
