"""Tests for lifecycle_invariants scope-path append_jsonl AST resolution."""

from __future__ import annotations

from app.core.companion_harness.companion import lifecycle_invariants as inv
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)


def test_append_jsonl_literal_paths_resolves_default_memory_store_scope_paths() -> (
    None
):
    rel = (
        "tests/app/core/companion_harness/companion/"
        "lifecycle_invariants_scope_append_fixture.py"
    )
    paths = inv.append_jsonl_literal_paths(rel)
    assert DEFAULT_MEMORY_STORE_SCOPE_PATHS.tool_background_jsonl in paths
