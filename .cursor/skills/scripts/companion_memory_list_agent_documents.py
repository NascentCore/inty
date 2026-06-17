#!/usr/bin/env python3
"""List or dump all companion MemoryStore documents (MemDocs) for an agent_id.

Uses MemoryStore.iter_stored_relative_paths and read_document_if_exists against
Postgres-backed SqlAlchemyMemoryRepository. For debugging and investigation.
See .cursor/skills/inspect-companion-harness/list-agent-documents/SKILL.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from companion_memory_inspect_lib import (
    DocumentVersionRow,
    apply_inty_config_env,
    iter_scope_documents_via_memory_store,
    list_companion_scopes,
    list_latest_document_kinds,
    load_database_dsn,
    open_memory_store,
    resolve_scope,
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Retrieve all MemoryStore documents for a companion (agent_id) for debugging."
        )
    )
    parser.add_argument(
        "--companion-id",
        required=True,
        help="WebSocket/API agent_id (MemoryStore companion_id)",
    )
    parser.add_argument("--user-id", default="", help="MemoryStore user_id scope")
    parser.add_argument("--chat-id", default="", help="MemoryStore chat_id scope")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Repo-root YAML with database block (default: config.yaml)",
    )
    parser.add_argument(
        "--list-scopes",
        action="store_true",
        help="List (user_id, chat_id) scopes for --companion-id and exit",
    )
    parser.add_argument(
        "--all-scopes",
        action="store_true",
        help="Dump every scope for this companion_id (default: one resolved scope)",
    )
    parser.add_argument(
        "--meta-only",
        action="store_true",
        help="Print paths and version metadata only, not document bodies",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit one JSON object per scope (meta + optional content)",
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help="Write each document body under DIR/<companion_id>/<chat_id>/<path>",
    )
    args = parser.parse_args()

    apply_inty_config_env(args.config)

    if args.list_scopes:
        scopes = list_companion_scopes(args.companion_id)
        if not scopes:
            sys.stdout.write(f"No scopes for companion_id={args.companion_id!r}\n")
            return 1
        for scope in scopes:
            sys.stdout.write(
                f"user_id={scope.user_id!r} chat_id={scope.chat_id!r}\n"
            )
        return 0

    if args.all_scopes:
        scopes = list_companion_scopes(args.companion_id)
        if not scopes:
            raise SystemExit(f"No MemoryStore rows for companion_id={args.companion_id!r}")
    else:
        scopes = [
            resolve_scope(
                companion_id=args.companion_id,
                user_id=args.user_id,
                chat_id=args.chat_id,
            )
        ]

    dsn = load_database_dsn()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else None
    exit_code = 0

    for scope in scopes:
        if args.json:
            store = open_memory_store(scope, dsn=dsn)
            meta_rows = {
                r.relative_path: r for r in list_latest_document_kinds(scope)
            }
            payload = {
                "scope": scope.registry_key(),
                "companion_id": scope.companion_id,
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
                if not args.meta_only and body is not None:
                    entry["content"] = body
                payload["documents"].append(entry)
            sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
            continue

        _scope_banner(scope.registry_key())
        missing = _dump_scope(
            scope=scope,
            dsn=dsn,
            meta_only=args.meta_only,
            output_dir=output_dir,
        )
        if missing:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
