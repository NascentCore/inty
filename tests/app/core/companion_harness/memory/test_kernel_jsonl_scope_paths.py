"""Smoke tests: kernel JSONL writers use MemoryStoreScopePaths accessors (#3413).

Generated entirely by Cursor agent.
"""

from __future__ import annotations

from app.core.companion_harness.companion.ai_private_prompt import (
    append_ai_private_thought,
)
from app.core.companion_harness.companion.runtime_events import (
    append_runtime_event,
    read_runtime_events,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)


def test_runtime_events_persist_on_scope_accessor_path(tmp_path) -> None:
    scope = CompanionScope("kern-ev", "agent-1", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.companion_runtime_events_jsonl

    append_runtime_event(store, {"kind": "tool_timeout", "ts": "2026-01-01T00:00:00+00:00"})

    raw = store.read_document_if_exists(rel)
    assert raw is not None
    assert "tool_timeout" in raw
    rows = read_runtime_events(store, kinds={"tool_timeout"}, limit=1)
    assert len(rows) == 1


def test_ai_private_thought_persist_on_scope_accessor_path(tmp_path) -> None:
    scope = CompanionScope("kern-ap", "agent-1", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.ai_private_jsonl

    append_ai_private_thought(store, text="inner line", after_user_msg_uuid=None)

    raw = store.read_document_if_exists(rel)
    assert raw is not None
    assert "inner line" in raw
