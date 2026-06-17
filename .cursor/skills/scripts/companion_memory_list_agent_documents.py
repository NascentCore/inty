#!/usr/bin/env python3
"""List or dump all companion MemoryStore documents (MemDocs) for an agent_id.

Uses MemoryStore.iter_stored_relative_paths and read_document_if_exists against
Postgres-backed SqlAlchemyMemoryRepository. For debugging and investigation.
See .cursor/skills/inspect-companion-harness/list-agent-documents/SKILL.md.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import cyclopts

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from companion_memory_inspect_lib import (
    DocumentVersionRow,
    apply_inty_config_env,
    iter_scope_documents_via_memory_store,
    list_agent_scopes,
    list_latest_document_kinds,
    load_database_dsn,
    open_memory_store,
    resolve_scope,
)

app = cyclopts.App(
    help=(
        "Retrieve all MemoryStore documents for an agent_id for debugging.\n\n"
        "Config: same as backend — ``INTY_CONFIG_YAML`` env or ``--config``; "
        "see ``app.core.config``."
    ),
)


def _scope_banner(scope_key: str) -> None:
    sys.stdout.write(f"\n=== scope {scope_key} ===\n")


def _print_doc_meta(row: DocumentVersionRow) -> None:
    sys.stdout.write(
        f"{row.relative_path}\t"
        f"sequence_id={row.sequence_id}\t"
        f"chars={row.content_chars}\t"
        f"created_at={row.created_at}\n"
    )


def _dump_scope(
    *,
    scope,
    dsn: str,
    meta_only: bool,
    output_dir: Path | None,
) -> int:
    store = open_memory_store(scope, dsn=dsn)
    meta_rows = {r.relative_path: r for r in list_latest_document_kinds(scope)}
    docs = iter_scope_documents_via_memory_store(store)
    if not docs:
        sys.stdout.write("(no documents in MemoryStore for this scope)\n")
        return 0

    missing = 0
    for rel, body in docs:
        row = meta_rows.get(rel)
        if row is not None:
            _print_doc_meta(row)
        else:
            sys.stdout.write(f"{rel}\t(no ORM metadata row)\n")
        if body is None:
            missing += 1
            continue
        if meta_only:
            continue
        if output_dir is not None:
            dest = output_dir / scope.companion_id / scope.chat_id / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(body, encoding="utf-8")
            sys.stdout.write(f"  -> {dest}\n")
        else:
            sys.stdout.write("---\n")
            sys.stdout.write(body)
            if body and not body.endswith("\n"):
                sys.stdout.write("\n")
    return missing


def _run_list_agent_documents(
    *,
    agent_id: str,
    user_id: str | None,
    chat_id: str | None,
    config: str | None,
    list_scopes: bool,
    all_scopes: bool,
    meta_only: bool,
    as_json: bool,
    output_dir: str | None,
) -> int:
    assert agent_id
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

    if all_scopes:
        scopes = list_agent_scopes(agent_id)
        if not scopes:
            raise SystemExit(f"No MemoryStore rows for agent_id={agent_id!r}")
    else:
        scopes = [resolve_scope(agent_id=agent_id, user_id=uid, chat_id=cid)]

    dsn = load_database_dsn()
    out_dir = Path(output_dir).resolve() if output_dir else None
    exit_code = 0

    for scope in scopes:
        if as_json:
            store = open_memory_store(scope, dsn=dsn)
            meta_rows = {
                r.relative_path: r for r in list_latest_document_kinds(scope)
            }
            payload = {
                "scope": scope.registry_key(),
                "agent_id": scope.companion_id,
                "user_id": scope.user_id,
                "chat_id": scope.chat_id,
                "documents": [],
            }
            for rel, body in iter_scope_documents_via_memory_store(store):
                row = meta_rows.get(rel)
                entry = {
                    "relative_path": rel,
                    "sequence_id": row.sequence_id if row else None,
                    "created_at": row.created_at if row else None,
                    "content_chars": len(body) if body is not None else 0,
                }
                if not meta_only and body is not None:
                    entry["content"] = body
                payload["documents"].append(entry)
            sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
            continue

        _scope_banner(scope.registry_key())
        missing = _dump_scope(
            scope=scope,
            dsn=dsn,
            meta_only=meta_only,
            output_dir=out_dir,
        )
        if missing:
            exit_code = 1
    return exit_code


@app.default
def main(
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
    list_scopes: Annotated[
        bool,
        cyclopts.Parameter(
            name="--list-scopes",
            help="List (user_id, chat_id) scopes for --agent-id and exit",
        ),
    ] = False,
    all_scopes: Annotated[
        bool,
        cyclopts.Parameter(
            name="--all-scopes",
            help="Dump every scope for this agent_id (default: one resolved scope)",
        ),
    ] = False,
    meta_only: Annotated[
        bool,
        cyclopts.Parameter(
            name="--meta-only",
            help="Print paths and version metadata only, not document bodies",
        ),
    ] = False,
    as_json: Annotated[
        bool,
        cyclopts.Parameter(
            name="--json",
            help="Emit one JSON object per scope (meta + optional content)",
        ),
    ] = False,
    output_dir: Annotated[
        str | None,
        cyclopts.Parameter(
            name="--output-dir",
            help="Write each document body under DIR/<agent_id>/<chat_id>/<path>",
        ),
    ] = None,
) -> None:
    raise SystemExit(
        _run_list_agent_documents(
            agent_id=agent_id,
            user_id=user_id,
            chat_id=chat_id,
            config=config,
            list_scopes=list_scopes,
            all_scopes=all_scopes,
            meta_only=meta_only,
            as_json=as_json,
            output_dir=output_dir,
        )
    )


if __name__ == "__main__":
    app()
