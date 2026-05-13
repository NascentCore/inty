from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.core.companion_harness.companion.memory_registry import get_memory_store
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.companion_tool_runtime import execute_tool_call
from app.core.companion_harness.companion.tools import WRITABLE_RELATIVE_PATHS


def _run_tool(
    store,
    name: str,
    args: str,
    *,
    write_allowlist: frozenset[str] | None = None,
) -> str:
    if write_allowlist is not None:
        return asyncio.run(
            execute_tool_call(store, name, args, write_allowlist=write_allowlist)
        )
    return asyncio.run(execute_tool_call(store, name, args))


def test_tool_memory_store_list_paths(tmp_path: Path) -> None:
    st = get_memory_store(CompanionScope("tools", "a", tmp_path.name), dsn="")
    st.write_document("USER.md", "u")
    st.write_document("memory/daily/2099-01-01.md", "d")
    out = _run_tool(
        st,
        "memory_store_list_paths",
        json.dumps({"relative_path": "."}),
    )
    assert "USER.md" in out
    assert "memory/" in out
    out_mem = _run_tool(
        st,
        "memory_store_list_paths",
        json.dumps({"relative_path": "memory"}),
    )
    assert "daily/" in out_mem


def test_tool_memory_store_read_write(tmp_path: Path) -> None:
    st = get_memory_store(CompanionScope("tools", "a", f"{tmp_path.name}-rw"), dsn="")
    w = _run_tool(
        st,
        "memory_store_write_document",
        json.dumps({"relative_path": "USER.md", "content": "full text"}),
        write_allowlist=WRITABLE_RELATIVE_PATHS,
    )
    assert w.startswith("OK ")
    r = _run_tool(
        st,
        "memory_store_read_document",
        json.dumps({"relative_path": "USER.md"}),
    )
    assert r == "full text"


def test_tool_memory_store_write_not_in_allowlist(tmp_path: Path) -> None:
    st = get_memory_store(CompanionScope("tools", "a", f"{tmp_path.name}-wl"), dsn="")
    out = _run_tool(
        st,
        "memory_store_write_document",
        json.dumps({"relative_path": "secret.txt", "content": "nope"}),
        write_allowlist=WRITABLE_RELATIVE_PATHS,
    )
    assert out.startswith("ERROR:")
    assert "only allows" in out
