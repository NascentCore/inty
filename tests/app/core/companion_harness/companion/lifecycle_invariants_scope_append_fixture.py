"""AST fixture: append_jsonl_record via DEFAULT_MEMORY_STORE_SCOPE_PATHS (HYGIENE-2026-488).

Generated entirely by the maintenance cron agent for lifecycle_invariants tests.
"""

from __future__ import annotations

from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)


def append_tool_background_via_scope_accessor(store: MemoryStore) -> None:
    store.append_jsonl_record(
        DEFAULT_MEMORY_STORE_SCOPE_PATHS.tool_background_jsonl,
        {"kind": "fixture"},
    )
