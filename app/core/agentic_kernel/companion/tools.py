"""Companion workspace tools: 定义与执行。"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .file_store import read_text, write_text
from .memory_store import MemoryStore
from .workspace import WorkspacePaths

WORKSPACE_READ_FILE_MAX_CHARS_CAP: int = 120_000

WRITABLE_RELATIVE_PATHS: frozenset[str] = frozenset(
    {
        "AGENTS.md",
        "CAPABILITIES.md",
        "HEARTBEAT.md",
        "IDENTITY.md",
        "MEMORY.md",
        "SOUL.md",
        "TOOLS.md",
        "USER.md",
    }
)

_INNER_TICK_TOOL_FUNCTION_NAMES: tuple[str, ...] = (
    "user_profile_record",
    "workspace_list_dir",
    "workspace_read_file",
    "workspace_write_file",
)


def build_companion_tools() -> list[dict[str, Any]]:
    """Return OpenAI function tool schemas for companion tools."""
    return [
        {
            "type": "function",
            "function": {
                "name": "user_profile_record",
                "description": "Record a durable fact about the user into USER.md.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "fact": {
                            "type": "string",
                            "description": "The fact to record about the user.",
                        },
                    },
                    "required": ["fact"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "schedule_task",
                "description": "Schedule a future reminder or task.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "exec_time_utc": {
                            "type": "string",
                            "description": "ISO8601 datetime with timezone for when to fire.",
                        },
                        "task_text": {
                            "type": "string",
                            "description": "What to remind the user about.",
                        },
                    },
                    "required": ["exec_time_utc", "task_text"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "workspace_read_file",
                "description": "Read a file from the workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path within workspace.",
                        },
                        "max_chars": {
                            "type": "integer",
                            "description": "Optional max characters to return.",
                        },
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "workspace_write_file",
                "description": "Write (overwrite) a workspace document.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path (must be in writable allowlist).",
                        },
                        "content": {
                            "type": "string",
                            "description": "Full file content to write.",
                        },
                    },
                    "required": ["path", "content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "workspace_list_dir",
                "description": "List files and directories in a workspace path.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative directory path (default: root).",
                        },
                    },
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "workspace_mkdir",
                "description": "Create a directory in the workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative directory path to create.",
                        },
                    },
                    "required": ["path"],
                },
            },
        },
    ]


def build_companion_tools_inner_tick() -> list[dict[str, Any]]:
    full = build_companion_tools()
    want = set(_INNER_TICK_TOOL_FUNCTION_NAMES)
    picked = [
        t
        for t in full
        if t.get("type") == "function" and t.get("function", {}).get("name") in want
    ]
    by_name = {t["function"]["name"]: t for t in picked}
    missing = want - set(by_name)
    if missing:
        raise RuntimeError(
            "build_companion_tools_inner_tick: missing tool defs "
            + ", ".join(sorted(missing))
        )
    return [by_name[n] for n in _INNER_TICK_TOOL_FUNCTION_NAMES]


def execute_tool_call(
    root: Path,
    store: MemoryStore,
    name: str,
    raw_arguments: str,
    *,
    write_allowlist: frozenset[str] = WRITABLE_RELATIVE_PATHS,
) -> str:
    """Execute a companion tool call. Returns result string (ERROR: prefix on failure)."""
    try:
        args = json.loads(raw_arguments) if raw_arguments else {}
    except json.JSONDecodeError as e:
        return f"ERROR: invalid JSON arguments: {e}"

    if name == "user_profile_record":
        return _tool_user_profile_record(root, store, args)
    elif name == "schedule_task":
        return _tool_schedule_task(root, args)
    elif name == "workspace_read_file":
        return _tool_workspace_read_file(root, store, args)
    elif name == "workspace_write_file":
        return _tool_workspace_write_file(root, store, args, write_allowlist)
    elif name == "workspace_list_dir":
        return _tool_workspace_list_dir(root, args)
    elif name == "workspace_mkdir":
        return _tool_workspace_mkdir(root, args)
    else:
        return f"ERROR: unknown tool: {name}"


def _resolve_workspace_path(root: Path, rel: str) -> Path | str:
    """Resolve and validate a workspace-relative path. Returns Path or error string."""
    rel = (rel or "").strip().replace("\\", "/")
    if not rel:
        return "ERROR: path is empty"
    if rel.startswith("/"):
        return "ERROR: path must be relative"
    resolved = (root / rel).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        return "ERROR: path escapes workspace"
    return resolved


def _tool_user_profile_record(root: Path, store: MemoryStore, args: dict) -> str:
    fact = (args.get("fact") or "").strip()
    if not fact:
        return "ERROR: fact is empty"
    user_md = store.read_document_if_exists("USER.md") or ""
    section_header = "## 身份信息"
    if section_header not in user_md:
        updated = user_md.rstrip("\n") + f"\n\n{section_header}\n\n- {fact}\n"
    else:
        idx = user_md.index(section_header)
        end = idx + len(section_header)
        next_section = user_md.find("\n## ", end)
        if next_section == -1:
            updated = user_md.rstrip("\n") + f"\n- {fact}\n"
        else:
            before = user_md[:next_section].rstrip("\n")
            after = user_md[next_section:]
            updated = before + f"\n- {fact}\n" + after
    store.write_document("USER.md", updated)
    return f"OK: recorded fact into USER.md"


def _tool_schedule_task(root: Path, args: dict) -> str:
    exec_time = (args.get("exec_time_utc") or "").strip()
    task_text = (args.get("task_text") or "").strip()
    if not exec_time or not task_text:
        return "ERROR: exec_time_utc and task_text are required"
    paths = WorkspacePaths(root=root)
    queue_path = paths.schedule_queue_json
    tasks: list[dict] = []
    if queue_path.is_file():
        try:
            tasks = json.loads(read_text(queue_path))
        except json.JSONDecodeError:
            tasks = []
    tasks.append(
        {
            "id": str(uuid.uuid4()),
            "exec_time_utc": exec_time,
            "task_text": task_text,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    write_text(queue_path, json.dumps(tasks, ensure_ascii=False, indent=2) + "\n")
    return f"OK: scheduled task for {exec_time}"


def _tool_workspace_read_file(root: Path, store: MemoryStore, args: dict) -> str:
    rel = (args.get("path") or "").strip()
    max_chars = args.get("max_chars")
    result = _resolve_workspace_path(root, rel)
    if isinstance(result, str):
        return result
    content = store.read_document_if_exists(rel)
    if content is None:
        if not store.allow_workspace_disk_fallback:
            return f"ERROR: file not found: {rel}"
        if not result.is_file():
            return f"ERROR: file not found: {rel}"
        content = read_text(result)
    if max_chars is not None and isinstance(max_chars, int) and max_chars > 0:
        cap = min(max_chars, WORKSPACE_READ_FILE_MAX_CHARS_CAP)
        if len(content) > cap:
            content = content[:cap] + f"\n... (truncated at {cap} chars)"
    elif len(content) > WORKSPACE_READ_FILE_MAX_CHARS_CAP:
        content = (
            content[:WORKSPACE_READ_FILE_MAX_CHARS_CAP]
            + f"\n... (truncated at {WORKSPACE_READ_FILE_MAX_CHARS_CAP} chars)"
        )
    return content


def _tool_workspace_write_file(
    root: Path, store: MemoryStore, args: dict, allowlist: frozenset[str]
) -> str:
    rel = (args.get("path") or "").strip()
    content = args.get("content", "")
    if not rel:
        return "ERROR: path is empty"
    if rel not in allowlist:
        return f"ERROR: path {rel} is not in writable allowlist"
    result = _resolve_workspace_path(root, rel)
    if isinstance(result, str):
        return result
    store.write_document(rel, content)
    return f"OK: wrote {len(content)} chars to {rel}"


def _tool_workspace_list_dir(root: Path, args: dict) -> str:
    rel = (args.get("path") or "").strip() or "."
    result = _resolve_workspace_path(root, rel)
    if isinstance(result, str):
        return result
    if not result.is_dir():
        return f"ERROR: not a directory: {rel}"
    entries = sorted(result.iterdir())
    lines = []
    for entry in entries:
        name = entry.name
        if entry.is_dir():
            name += "/"
        lines.append(name)
    if not lines:
        return "(empty directory)"
    return "\n".join(lines)


def _tool_workspace_mkdir(root: Path, args: dict) -> str:
    rel = (args.get("path") or "").strip()
    result = _resolve_workspace_path(root, rel)
    if isinstance(result, str):
        return result
    result.mkdir(parents=True, exist_ok=True)
    return f"OK: directory {rel} exists"
