#!/usr/bin/env python3
"""Print one companion MemoryStore document (MemDoc) from Postgres via MemoryStore API.

For debugging bootstrap, LangSmith memory_store_write_document, and append-only versions.
See .cursor/skills/inspect-companion-harness/show-memory-document/SKILL.md.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import cyclopts

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from companion_memory_inspect_lib import (
    apply_inty_config_env,
    fetch_document_versions,
    list_agent_scopes,
    list_latest_document_kinds,
    load_database_dsn,
    open_memory_store,
    resolve_scope,
)

app = cyclopts.App(
    help=(
        "Print latest (or recent) companion MemoryStore document bodies for debugging.\n\n"
        "Config: same as backend — ``INTY_CONFIG_YAML`` env or ``--config``; "
        "see ``app.core.config``."
    ),
)


def _print_version_meta(row) -> None:
    sys.stdout.write(
        f"sequence_id={row.sequence_id} "
        f"created_at={row.created_at} "
        f"record_uuid={row.record_uuid} "
        f"chars={row.content_chars}\n"
    )


def _run_show_document(
    *,
    document: str | None,
    agent_id: str,
    user_id: str | None,
    chat_id: str | None,
    config: str | None,
    limit: int,
    meta_only: bool,
    list_scopes: bool,
    list_kinds: bool,
) -> int:
    assert agent_id
    assert limit >= 1
    apply_inty_config_env(config)
    uid = (user_id or "").strip()
    cid = (chat_id or "").strip()

    if list_scopes:
        scopes = list_agent_scopes(agent_id)
        if not scopes:
            sys.stdout.write(f"No scopes for agent_id={agent_id!r}\n")
            return 1
        for scope in scopes:
            sys.stdout.write(
                f"user_id={scope.user_id!r} chat_id={scope.chat_id!r}\n"
            )
        return 0

    scope = resolve_scope(agent_id=agent_id, user_id=uid, chat_id=cid)
    sys.stdout.write(f"scope={scope.registry_key()}\n")

    if list_kinds:
        rows = list_latest_document_kinds(scope)
        for row in rows:
            sys.stdout.write(f"{row.relative_path}\t")
            _print_version_meta(row)
        return 0

    if not document:
        sys.stderr.write(
            "DOCUMENT positional argument required unless --list-scopes or --list-kinds.\n"
        )
        return 2

    dsn = load_database_dsn()
    store = open_memory_store(scope, dsn=dsn)
    versions = fetch_document_versions(scope, document, limit=limit)
    if not versions:
        paths = store.iter_stored_relative_paths()
        hint = ""
        if paths:
            hint = f" Known paths: {', '.join(paths)}"
        sys.stderr.write(f"Document not found: {document!r}.{hint}\n")
        return 1

    for idx, row in enumerate(versions):
        if limit > 1:
            sys.stdout.write(f"--- version {idx + 1}/{len(versions)} ---\n")
        _print_version_meta(row)
        if not meta_only:
            sys.stdout.write(row.content)
            if row.content and not row.content.endswith("\n"):
                sys.stdout.write("\n")
    return 0


@app.default
def main(
    document: Annotated[
        str | None,
        cyclopts.Parameter(
            help=(
                "Scope-relative path, e.g. STYLE.md, context.json, "
                "memory/daily/2026-05-18.md"
            ),
        ),
    ] = None,
    *,
    agent_id: Annotated[
        str,
        cyclopts.Parameter(
            name="--agent-id",
            help="WebSocket/API agent_id (MemoryStore companion_id column)",
        ),
    ],
    user_id: Annotated[
        str | None,
        cyclopts.Parameter(
            name="--user-id",
            help="MemoryStore user_id scope",
        ),
    ] = None,
    chat_id: Annotated[
        str | None,
        cyclopts.Parameter(
            name="--chat-id",
            help="MemoryStore chat_id scope",
        ),
    ] = None,
    config: Annotated[
        str | None,
        cyclopts.Parameter(
            name="--config",
            help=(
                "Inty YAML path (sets INTY_CONFIG_YAML). "
                "When omitted: existing INTY_CONFIG_YAML env, else config.yaml."
            ),
        ),
    ] = None,
    limit: Annotated[
        int,
        cyclopts.Parameter(
            name="--limit",
            help="Print the N most recent versions (default: 1)",
        ),
    ] = 1,
    meta_only: Annotated[
        bool,
        cyclopts.Parameter(
            name="--meta-only",
            help="Print version metadata only, not document body",
        ),
    ] = False,
    list_scopes: Annotated[
        bool,
        cyclopts.Parameter(
            name="--list-scopes",
            help="List (user_id, chat_id) scopes for --agent-id and exit",
        ),
    ] = False,
    list_kinds: Annotated[
        bool,
        cyclopts.Parameter(
            name="--list-kinds",
            help="List latest document_kind rows for the resolved scope and exit",
        ),
    ] = False,
) -> None:
    raise SystemExit(
        _run_show_document(
            document=document,
            agent_id=agent_id,
            user_id=user_id,
            chat_id=chat_id,
            config=config,
            limit=limit,
            meta_only=meta_only,
            list_scopes=list_scopes,
            list_kinds=list_kinds,
        )
    )


if __name__ == "__main__":
    app()
