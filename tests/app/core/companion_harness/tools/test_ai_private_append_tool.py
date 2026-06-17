from __future__ import annotations

import json
from pathlib import Path

from app.core.companion_harness.companion.ai_private_prompt import (
    load_ai_private_thoughts,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.tools.companion_tool_runtime import execute_tool_call


async def test_ai_private_append_tool_records_thought(tmp_path: Path) -> None:
    store = MemoryStore(
        scope=CompanionScope("ap-tool", "a", tmp_path.name),
        repository=None,
    )
    result = await execute_tool_call(
        store,
        "ai_private_append",
        json.dumps({"text": "quiet worry about his silence"}),
    )
    assert result.startswith("OK recorded ai_private uuid=")
    thoughts = load_ai_private_thoughts(store)
    assert len(thoughts) == 1
    assert thoughts[0].text == "quiet worry about his silence"
    raw = store.read_document("ai_private.jsonl")
    row = json.loads(raw.strip().splitlines()[0])
    assert row["uuid"] == thoughts[0].uuid
    assert row["text"] == thoughts[0].text
