from __future__ import annotations

import json

import pytest

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.tools.companion_tool_runtime import (
    execute_tool_call_blocking,
)


@pytest.fixture
def store() -> MemoryStore:
    return MemoryStore(scope=CompanionScope("u", "a", "set-bgm"), repository=None)


def test_execute_set_bgm_tool_ok(store: MemoryStore) -> None:
    out = execute_tool_call_blocking(
        store,
        "set_bgm",
        json.dumps({"track_id": "warm_chat_02", "reason": "warmer tone"}),
    )
    assert out.startswith("OK ")
    data = json.loads(out[3:])
    assert data["track_id"] == "warm_chat_02"


def test_execute_set_bgm_tool_unknown(store: MemoryStore) -> None:
    bad = execute_tool_call_blocking(
        store,
        "set_bgm",
        json.dumps({"track_id": "missing_track_xyz", "reason": "x"}),
    )
    assert bad.startswith("ERROR:")
