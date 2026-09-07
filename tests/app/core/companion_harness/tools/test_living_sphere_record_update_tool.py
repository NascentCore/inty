from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)
from app.core.companion_harness.tools.companion_tool_runtime import (
    execute_tool_call,
)
from app.living_sphere.models import LIVING_SPHERE_RECORD_UPDATE_TOOL_NAME


@pytest.mark.asyncio
async def test_living_sphere_record_update_appends_jsonl(
    tmp_path: Path,
) -> None:
    root = tmp_path / "ls-tool"
    root.mkdir()
    store = MemoryStore(
        scope=CompanionScope("u-ls", "c-ls", str(root.resolve())),
        repository=None,
    )
    out = await execute_tool_call(
        store,
        LIVING_SPHERE_RECORD_UPDATE_TOOL_NAME,
        json.dumps({"change_request": "把沙发挪到窗边"}, ensure_ascii=False),
    )
    assert out.startswith("OK recorded update_id=")
    body = store.read_document(
        DEFAULT_MEMORY_STORE_SCOPE_PATHS.living_sphere_updates_jsonl
    )
    lines = [ln for ln in body.strip().split("\n") if ln.strip()]
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["change_request"] == "把沙发挪到窗边"
    assert row["source"] == "chat_tool"


@pytest.mark.asyncio
async def test_living_sphere_record_update_rejects_empty_change(
    tmp_path: Path,
) -> None:
    root = tmp_path / "ls-tool-err"
    root.mkdir()
    store = MemoryStore(
        scope=CompanionScope("u-ls2", "c-ls2", str(root.resolve())),
        repository=None,
    )
    out = await execute_tool_call(
        store,
        LIVING_SPHERE_RECORD_UPDATE_TOOL_NAME,
        '{"change_request":"   "}',
    )
    assert out.startswith("ERROR:")
