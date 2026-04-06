from __future__ import annotations

import json
from pathlib import Path

from app.core.agentic_kernel.companion.memory_store import MemoryStore
from app.core.agentic_kernel.companion.tools import (
    WRITABLE_RELATIVE_PATHS,
    build_companion_tools,
    execute_tool_call,
)


def test_build_companion_tools() -> None:
    tools = build_companion_tools()
    names = [t["function"]["name"] for t in tools]
    assert len(tools) == 6
    assert names == [
        "user_profile_record",
        "schedule_task",
        "workspace_read_file",
        "workspace_write_file",
        "workspace_list_dir",
        "workspace_mkdir",
    ]


def test_tool_workspace_list_dir(tmp_path: Path) -> None:
    root = tmp_path
    (root / "a.txt").write_text("x", encoding="utf-8")
    sub = root / "d"
    sub.mkdir()
    (sub / "inner.md").write_text("y", encoding="utf-8")
    store = MemoryStore(workspace_root=root, repository=None, mirror_to_files=True)
    out = execute_tool_call(
        root,
        store,
        "workspace_list_dir",
        json.dumps({"path": "."}),
    )
    assert "a.txt" in out
    assert "d/" in out


def test_tool_workspace_read_write(tmp_path: Path) -> None:
    root = tmp_path
    store = MemoryStore(workspace_root=root, repository=None, mirror_to_files=True)
    w = execute_tool_call(
        root,
        store,
        "workspace_write_file",
        json.dumps({"path": "USER.md", "content": "full text"}),
    )
    assert w.startswith("OK:")
    r = execute_tool_call(
        root,
        store,
        "workspace_read_file",
        json.dumps({"path": "USER.md"}),
    )
    assert r == "full text"


def test_tool_workspace_write_not_in_allowlist(tmp_path: Path) -> None:
    root = tmp_path
    store = MemoryStore(workspace_root=root, repository=None, mirror_to_files=True)
    out = execute_tool_call(
        root,
        store,
        "workspace_write_file",
        json.dumps({"path": "secret.txt", "content": "nope"}),
        write_allowlist=WRITABLE_RELATIVE_PATHS,
    )
    assert out.startswith("ERROR:")
    assert "allowlist" in out
