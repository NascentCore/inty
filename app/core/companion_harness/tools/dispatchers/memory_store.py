from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.tools.companion_tool_definitions import (
    CompanionToolName,
)


def _dispatch_memory_store_list_paths(
    store: MemoryStore,
    arguments: dict[str, Any],
    tool_memory_store_list_paths: Callable[[MemoryStore, str], str],
) -> str:
    rel = str(arguments.get("relative_path", ""))
    return tool_memory_store_list_paths(store, rel)


def _dispatch_memory_store_read_document(
    store: MemoryStore,
    arguments: dict[str, Any],
    tool_memory_store_read_document: Callable[
        [MemoryStore, str, int | None], str
    ],
    parse_optional_max_chars: Callable[[Any], int | None],
) -> str:
    rel = str(arguments.get("relative_path", ""))
    try:
        max_chars = parse_optional_max_chars(arguments.get("max_chars"))
    except ValueError as exc:
        return f"ERROR: {exc}"
    return tool_memory_store_read_document(store, rel, max_chars=max_chars)


def _dispatch_memory_store_write_document(
    store: MemoryStore,
    arguments: dict[str, Any],
    write_allowlist: frozenset[str] | None,
    tool_memory_store_write_document: Callable[[MemoryStore, str, str], str],
    write_document_allowlist_reject: Callable[
        [MemoryStore, str, frozenset[str]], str | None
    ],
) -> str:
    rel = str(arguments.get("relative_path", ""))
    content = str(arguments.get("content", ""))
    if write_allowlist is not None:
        blocked = write_document_allowlist_reject(
            store, rel, write_allowlist
        )
        if blocked is not None:
            return blocked
    return tool_memory_store_write_document(store, rel, content)


def dispatch_memory_store_tool(
    *,
    store: MemoryStore,
    name: str,
    arguments: dict[str, Any],
    write_allowlist: frozenset[str] | None,
    tool_memory_store_list_paths: Callable[[MemoryStore, str], str],
    tool_memory_store_read_document: Callable[
        [MemoryStore, str, int | None], str
    ],
    tool_memory_store_write_document: Callable[[MemoryStore, str, str], str],
    tool_memory_store_mkdir: Callable[[MemoryStore, str], str],
    tool_update_user_md: Callable[[MemoryStore, list[dict[str, Any]]], str],
    parse_optional_max_chars: Callable[[Any], int | None],
    write_document_allowlist_reject: Callable[
        [MemoryStore, str, frozenset[str]], str | None
    ],
) -> str | None:
    """Dispatch MemoryStore-oriented tool calls.

    Returns `None` when the tool name is not handled by this dispatcher.
    """
    match name:
        case "memory_store_list_paths":
            return _dispatch_memory_store_list_paths(
                store,
                arguments,
                tool_memory_store_list_paths,
            )
        case "memory_store_read_document":
            return _dispatch_memory_store_read_document(
                store,
                arguments,
                tool_memory_store_read_document,
                parse_optional_max_chars,
            )
        case "memory_store_write_document":
            return _dispatch_memory_store_write_document(
                store,
                arguments,
                write_allowlist,
                tool_memory_store_write_document,
                write_document_allowlist_reject,
            )
        case "memory_store_mkdir":
            rel = str(arguments.get("relative_path", ""))
            return tool_memory_store_mkdir(store, rel)
        case CompanionToolName.UPDATE_USER_MD.value:
            raw_items = arguments.get("items")
            if not isinstance(raw_items, list):
                return "ERROR: items must be a JSON array"
            return tool_update_user_md(store, raw_items)
        case _:
            return None
