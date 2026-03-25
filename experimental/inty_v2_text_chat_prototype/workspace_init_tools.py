"""Workspace bootstrap 工具：仅允许在 workspace 根目录内读写（与 agentic_ai_companion 工具模式对齐）。"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Callable

from .file_store import read_text, write_text

_USER_MD_REL = "USER.md"
_USER_PROFILE_SECTION = "## 基本信息记录"

# REPL 对话轮允许整文件覆盖写入的相对路径（根目录约定文档；不含 transcript/context 等）
REPL_WRITABLE_RELATIVE_PATHS: frozenset[str] = frozenset(
    {
        "AGENTS.md",
        "HEARTBEAT.md",
        "IDENTITY.md",
        "MEMORY.md",
        "SOUL.md",
        "TOOLS.md",
        "USER.md",
    }
)


def openai_assistant_message_dict(msg: Any) -> dict[str, Any]:
    """将 chat.completions assistant message 转为可回注 messages 列表的 dict（含 tool_calls）。"""
    raw_tool_calls = getattr(msg, "tool_calls", None)
    out: dict[str, Any] = {
        "role": "assistant",
        "content": msg.content if msg.content is not None else "",
    }
    if not raw_tool_calls:
        return out
    tool_calls: list[dict[str, Any]] = []
    for tc in raw_tool_calls:
        fn = tc.function
        tool_calls.append(
            {
                "id": tc.id,
                "type": getattr(tc, "type", "function"),
                "function": {
                    "name": fn.name,
                    "arguments": fn.arguments if fn.arguments is not None else "",
                },
            }
        )
    out["tool_calls"] = tool_calls
    return out


def append_user_profile_facts_to_user_md(text: str, new_bullets: list[str]) -> str:
    """
    在 USER.md 的「基本信息记录」小节追加条目；若尚无该小节则在文末追加。
    new_bullets 每项应为完整一行（含前导 `- `）。
    """
    lines = text.splitlines()
    if _USER_PROFILE_SECTION not in lines:
        block = "\n\n" + _USER_PROFILE_SECTION + "\n\n" + "\n".join(new_bullets)
        return text.rstrip() + block + "\n"
    idx = lines.index(_USER_PROFILE_SECTION)
    j = idx + 1
    while j < len(lines) and lines[j].strip() == "":
        j += 1
    insert_at = j
    while insert_at < len(lines) and not lines[insert_at].startswith("## "):
        insert_at += 1
    for k, b in enumerate(new_bullets):
        lines.insert(insert_at + k, b)
    return "\n".join(lines) + "\n"


def tool_user_profile_record(root: Path, items: list[dict[str, Any]]) -> str:
    """
    将用户自愿透露的基本信息追加写入 USER.md 的「基本信息记录」。
    items：每项含 label、value（均为非空短文本）。
    """
    p = resolve_under_workspace(root, _USER_MD_REL)
    if not p.is_file():
        return f"ERROR: missing {_USER_MD_REL!r}"
    today = date.today().isoformat()
    bullets: list[str] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        label = str(raw.get("label", "")).strip()
        value = str(raw.get("value", "")).strip()
        if not label or not value:
            continue
        bullets.append(f"- {label}：{value}（记录日期 {today}）")
    if not bullets:
        return "ERROR: no valid items (need label and value for each entry)"
    prev = read_text(p)
    merged = append_user_profile_facts_to_user_md(prev, bullets)
    write_text(p, merged)
    return f"OK appended {len(bullets)} line(s) to {_USER_MD_REL}"


def resolve_under_workspace(root: Path, relative_path: str) -> Path:
    """
    将相对路径解析为绝对路径；禁止逃出 workspace。
    空字符串表示 workspace 根目录。
    """
    root = root.resolve()
    rel = (relative_path or "").strip().replace("\\", "/")
    if rel.startswith("/"):
        raise ValueError("path must be relative to workspace root")
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("path escapes workspace root") from exc
    return candidate


def tool_workspace_list_dir(root: Path, relative_path: str) -> str:
    """列出目录下的直接子项（文件与目录名）；目录名以 / 结尾。"""
    d = resolve_under_workspace(root, relative_path)
    if not d.is_dir():
        return f"ERROR: not a directory: {relative_path!r}"
    names = sorted(d.iterdir(), key=lambda p: p.name.lower())
    lines: list[str] = []
    for p in names:
        if p.name.startswith("."):
            continue
        lines.append(f"{p.name}/" if p.is_dir() else p.name)
    return "\n".join(lines) if lines else "(empty)"


def tool_workspace_read_file(root: Path, relative_path: str) -> str:
    p = resolve_under_workspace(root, relative_path)
    if not p.is_file():
        return f"ERROR: not a file: {relative_path!r}"
    return read_text(p)


def tool_workspace_write_file(root: Path, relative_path: str, content: str) -> str:
    p = resolve_under_workspace(root, relative_path)
    write_text(p, content)
    return f"OK wrote {len(content)} chars to {relative_path}"


def tool_workspace_mkdir(root: Path, relative_path: str) -> str:
    p = resolve_under_workspace(root, relative_path)
    p.mkdir(parents=True, exist_ok=True)
    return f"OK mkdir {relative_path}"


def build_openai_tools() -> list[dict[str, Any]]:
    """OpenAI Chat Completions `tools` 列表。"""
    return [
        {
            "type": "function",
            "function": {
                "name": "workspace_list_dir",
                "description": (
                    "List immediate children of a directory under the workspace root. "
                    "Use empty relative_path for the workspace root. "
                    "Directory names are shown with a trailing slash."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "relative_path": {
                            "type": "string",
                            "description": "Directory relative to workspace; use '' for root.",
                        },
                    },
                    "required": ["relative_path"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "workspace_read_file",
                "description": "Read a UTF-8 text file under the workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "relative_path": {
                            "type": "string",
                            "description": "File path relative to workspace root.",
                        },
                    },
                    "required": ["relative_path"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "workspace_write_file",
                "description": (
                    "Create or overwrite a UTF-8 text file under the workspace. "
                    "Creates parent directories as needed."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "relative_path": {
                            "type": "string",
                            "description": "File path relative to workspace root.",
                        },
                        "content": {
                            "type": "string",
                            "description": "Full file content.",
                        },
                    },
                    "required": ["relative_path", "content"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "workspace_mkdir",
                "description": "Create a directory under the workspace (mkdir -p).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "relative_path": {
                            "type": "string",
                            "description": "Directory path relative to workspace root.",
                        },
                    },
                    "required": ["relative_path"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "user_profile_record",
                "description": (
                    "Append structured facts about the user to USER.md under «基本信息记录». "
                    "Call when the user shares durable basic info (e.g. age, how they wish to be called, "
                    "timezone) that should persist. Do not use for secrets unless the user clearly wants "
                    "them remembered. Speak to the user in companion language only; never mention tools, "
                    "JSON, or filenames."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "description": "One or more label/value pairs to append.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "label": {
                                        "type": "string",
                                        "description": "Short field name, e.g. 年龄、称呼偏好.",
                                    },
                                    "value": {
                                        "type": "string",
                                        "description": "What the user said or agreed to store.",
                                    },
                                },
                                "required": ["label", "value"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["items"],
                    "additionalProperties": False,
                },
            },
        },
    ]


def build_openai_repl_tools() -> list[dict[str, Any]]:
    """
    REPL 对话轮：用户档案追加 + 工作区文档读写（写入仅限 REPL_WRITABLE_RELATIVE_PATHS）。
    """
    full = build_openai_tools()
    by_name = {
        t["function"]["name"]: t
        for t in full
        if t.get("type") == "function" and "function" in t
    }
    names = (
        "user_profile_record",
        "workspace_list_dir",
        "workspace_read_file",
        "workspace_write_file",
    )
    out: list[dict[str, Any]] = []
    for n in names:
        t = by_name.get(n)
        if not t:
            raise KeyError(f"missing tool definition: {n!r}")
        if n == "workspace_write_file":
            w = dict(t)
            wfn = dict(w["function"])
            wfn["description"] = (
                "Create or overwrite a UTF-8 text file under the workspace. "
                "In REPL, only these root files are writable: "
                + ", ".join(sorted(REPL_WRITABLE_RELATIVE_PATHS))
                + ". When the user explicitly asks to change how you relate, boundaries, or "
                "persistent preferences, read the current file first (e.g. SOUL.md, USER.md), "
                "then write the full updated content. Do not use for transcript.jsonl or context.json."
            )
            w["function"] = wfn
            out.append(w)
        else:
            out.append(t)
    return out


def _repl_write_allowed(root: Path, relative_path: str, write_allowlist: frozenset[str]) -> str | None:
    """若不允许写入则返回错误信息字符串，否则 None。"""
    p = resolve_under_workspace(root, relative_path)
    rel_posix = p.relative_to(root.resolve()).as_posix()
    if rel_posix not in write_allowlist:
        return (
            "ERROR: REPL workspace_write_file only allows: "
            + ", ".join(sorted(write_allowlist))
            + f"; got {rel_posix!r}"
        )
    return None


def _dispatch(
    root: Path,
    name: str,
    arguments: dict[str, Any],
    *,
    write_allowlist: frozenset[str] | None = None,
) -> str:
    if name == "workspace_list_dir":
        rel = str(arguments.get("relative_path", ""))
        return tool_workspace_list_dir(root, rel)
    if name == "workspace_read_file":
        rel = str(arguments.get("relative_path", ""))
        return tool_workspace_read_file(root, rel)
    if name == "workspace_write_file":
        rel = str(arguments.get("relative_path", ""))
        content = str(arguments.get("content", ""))
        if write_allowlist is not None:
            blocked = _repl_write_allowed(root, rel, write_allowlist)
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
    return f"ERROR: unknown tool {name!r}"


def execute_tool_call(
    root: Path,
    name: str,
    arguments_json: str,
    *,
    write_allowlist: frozenset[str] | None = None,
) -> str:
    raw = (arguments_json or "").strip()
    try:
        parsed: dict[str, Any] = json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        return f"ERROR: invalid JSON arguments: {exc}"
    if not isinstance(parsed, dict):
        return "ERROR: tool arguments must be a JSON object"
    try:
        return _dispatch(root, name, parsed, write_allowlist=write_allowlist)
    except (OSError, ValueError) as exc:
        return f"ERROR: {exc}"


def tool_executor_for_root(root: Path) -> Callable[[str, str], str]:
    """返回 (name, arguments_json) -> result_str，供循环内调用。"""

    def run(name: str, arguments_json: str) -> str:
        return execute_tool_call(root, name, arguments_json, write_allowlist=None)

    return run
