from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


def dispatch_workspace_tool(
    *,
    root: Path,
    name: str,
    arguments: dict[str, Any],
    write_allowlist: frozenset[str] | None,
    tool_workspace_list_dir: Callable[[Path, str], str],
    tool_workspace_read_file: Callable[[Path, str, int | None], str],
    tool_workspace_write_file: Callable[[Path, str, str], str],
    tool_workspace_mkdir: Callable[[Path, str], str],
    tool_user_profile_record: Callable[[Path, list[dict[str, Any]]], str],
    parse_optional_max_chars: Callable[[Any], int | None],
    repl_write_allowed: Callable[[Path, str, frozenset[str]], str | None],
) -> str | None:
    """Dispatch workspace-oriented tool calls.

    Returns `None` when the tool name is not handled by this dispatcher.
    """
    if name == "workspace_list_dir":
        rel = str(arguments.get("relative_path", ""))
        return tool_workspace_list_dir(root, rel)
    if name == "workspace_read_file":
        rel = str(arguments.get("relative_path", ""))
        try:
            max_chars = parse_optional_max_chars(arguments.get("max_chars"))
        except ValueError as exc:
            return f"ERROR: {exc}"
        return tool_workspace_read_file(root, rel, max_chars=max_chars)
    if name == "workspace_write_file":
        rel = str(arguments.get("relative_path", ""))
        content = str(arguments.get("content", ""))
        if write_allowlist is not None:
            blocked = repl_write_allowed(root, rel, write_allowlist)
            if blocked is not None:
                return blocked
        return tool_workspace_write_file(root, rel, content)
    if name == "workspace_mkdir":
        rel = str(arguments.get("relative_path", ""))
        return tool_workspace_mkdir(root, rel)
    if name == "user_profile_record":
        raw_items = arguments.get("items")
        if not isinstance(raw_items, list):
            return "ERROR: items must be a JSON array"
        return tool_user_profile_record(root, raw_items)
    return None
