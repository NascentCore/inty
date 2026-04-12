from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.core.agentic_kernel.companion.memory_registry import get_memory_store
from app.core.agentic_kernel.companion.repl_workspace_tools import execute_tool_call
from app.core.agentic_kernel.companion.tools import (
    WRITABLE_RELATIVE_PATHS,
    build_companion_tools,
)


def _run_tool(
    root: Path,
    name: str,
    args: str,
    *,
    write_allowlist: frozenset[str] | None = None,
) -> str:
    if write_allowlist is not None:
        return asyncio.run(
            execute_tool_call(root, name, args, write_allowlist=write_allowlist)
        )
    return asyncio.run(execute_tool_call(root, name, args))


def test_build_companion_tools() -> None:
    tools = build_companion_tools()
    names = [t["function"]["name"] for t in tools]
    assert names == [
        "user_profile_record",
        "schedule_task",
        "workspace_list_dir",
        "workspace_read_file",
        "workspace_write_file",
        "tool_update_chat_settings",
        "google_web_search",
        "generate_image",
        "modify_image",
    ]


def test_tool_workspace_list_dir(tmp_path: Path) -> None:
    root = tmp_path
    (root / "a.txt").write_text("x", encoding="utf-8")
    sub = root / "d"
    sub.mkdir()
    (sub / "inner.md").write_text("y", encoding="utf-8")
    get_memory_store(root)
    out = _run_tool(
        root,
        "workspace_list_dir",
        json.dumps({"relative_path": "."}),
    )
    assert "a.txt" in out
    assert "d/" in out


def test_tool_workspace_read_write(tmp_path: Path) -> None:
    root = tmp_path
    get_memory_store(root)
    w = _run_tool(
        root,
        "workspace_write_file",
        json.dumps({"relative_path": "USER.md", "content": "full text"}),
        write_allowlist=WRITABLE_RELATIVE_PATHS,
    )
    assert w.startswith("OK ")
    r = _run_tool(
        root,
        "workspace_read_file",
        json.dumps({"relative_path": "USER.md"}),
    )
    assert r == "full text"


def test_tool_workspace_write_not_in_allowlist(tmp_path: Path) -> None:
    root = tmp_path
    get_memory_store(root)
    out = _run_tool(
        root,
        "workspace_write_file",
        json.dumps({"relative_path": "secret.txt", "content": "nope"}),
        write_allowlist=WRITABLE_RELATIVE_PATHS,
    )
    assert out.startswith("ERROR:")
    assert "only allows" in out
