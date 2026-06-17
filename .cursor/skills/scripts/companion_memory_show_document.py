#!/usr/bin/env python3
"""Print one companion MemoryStore document (MemDoc) from Postgres via MemoryStore API.

For debugging bootstrap, LangSmith memory_store_write_document, and append-only versions.
See .cursor/skills/inspect-companion-harness/show-memory-document/SKILL.md.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from companion_memory_inspect_lib import (
    apply_inty_config_env,
    fetch_document_versions,
    list_companion_scopes,
    list_latest_document_kinds,
    load_database_dsn,
    open_memory_store,
    resolve_scope,
)


def _print_version_meta(row) -> None:
    sys.stdout.write(
        f"sequence_id={row.sequence_id} "
        f"created_at={row.created_at} "
        f"record_uuid={row.record_uuid} "
        f"chars={row.content_chars}\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Print latest (or recent) companion MemoryStore document bodies for debugging."
        )
    )
    parser.add_argument(
        "document",
        help="Scope-relative path, e.g. STYLE.md, context.json, memory/daily/2026-05-18.md",
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
        "--limit",
        type=int,
        default=1,
        help="Print the N most recent versions (default: 1)",
    )
    parser.add_argument(
        "--meta-only",
        action="store_true",
        help="Print version metadata only, not document body",
    )
    parser.add_argument(
        "--list-scopes",
        action="store_true",
        help="List (user_id, chat_id) scopes for --companion-id and exit",
    )
    parser.add_argument(
        "--list-kinds",
        action="store_true",
        help="List latest document_kind rows for the resolved scope and exit",
    )
    args = parser.parse_args()
    assert args.limit >= 1

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

    scope = resolve_scope(
        companion_id=args.companion_id,
        user_id=args.user_id,
        chat_id=args.chat_id,
    )
    sys.stdout.write(f"scope={scope.registry_key()}\n")

    if args.list_kinds:
        rows = list_latest_document_kinds(scope)
        for row in rows:
            sys.stdout.write(f"{row.relative_path}\t")
            _print_version_meta(row)
        return 0

    dsn = load_database_dsn()
    store = open_memory_store(scope, dsn=dsn)
    rel = args.document
    versions = fetch_document_versions(scope, rel, limit=args.limit)
    if not versions:
        paths = store.iter_stored_relative_paths()
        hint = ""
        if paths:
            hint = f" Known paths: {', '.join(paths)}"
        sys.stderr.write(f"Document not found: {rel!r}.{hint}\n")
        return 1

    for idx, row in enumerate(versions):
        if args.limit > 1:
            sys.stdout.write(f"--- version {idx + 1}/{len(versions)} ---\n")
        _print_version_meta(row)
        if not args.meta_only:
            sys.stdout.write(row.content)
            if row.content and not row.content.endswith("\n"):
                sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
