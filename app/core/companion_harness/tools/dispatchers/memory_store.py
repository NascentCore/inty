from __future__ import annotations

from typing import Any, Callable

from app.core.companion_harness.memory.memory_store import MemoryStore


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
    tool_user_profile_record: Callable[
        [MemoryStore, list[dict[str, Any]]], str
    ],
    parse_optional_max_chars: Callable[[Any], int | None],
    write_document_allowlist_reject: Callable[
        [MemoryStore, str, frozenset[str]], str | None
    ],
) -> str | None:
    """Dispatch MemoryStore-oriented tool calls.

    Returns `None` when the tool name is not handled by this dispatcher.
    """
    if name == "memory_store_list_paths":
        rel = str(arguments.get("relative_path", ""))
        return tool_memory_store_list_paths(store, rel)
    if name == "memory_store_read_document":
        rel = str(arguments.get("relative_path", ""))
        try:
            max_chars = parse_optional_max_chars(arguments.get("max_chars"))
        except ValueError as exc:
            return f"ERROR: {exc}"
        return tool_memory_store_read_document(store, rel, max_chars=max_chars)
    if name == "memory_store_write_document":
        rel = str(arguments.get("relative_path", ""))
        content = str(arguments.get("content", ""))
        if write_allowlist is not None:
            blocked = write_document_allowlist_reject(
                store, rel, write_allowlist
            )
            if blocked is not None:
                return blocked
        return tool_memory_store_write_document(store, rel, content)
    if name == "memory_store_mkdir":
        rel = str(arguments.get("relative_path", ""))
        return tool_memory_store_mkdir(store, rel)
    if name == "user_profile_record":
        raw_items = arguments.get("items")
        if not isinstance(raw_items, list):
            return "ERROR: items must be a JSON array"
        return tool_user_profile_record(store, raw_items)
    return None
