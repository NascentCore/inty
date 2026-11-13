"""Smoke tests: tools/kernel JSONL writers use MemoryStoreScopePaths accessors (#3413).

Generated entirely by Cursor agent.
"""

from __future__ import annotations

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.living_sphere_curator import (
    _read_all_updates,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)
from app.core.companion_harness.tools.companion_user_feedback import (
    append_user_feedback_record,
)
from app.core.companion_harness.tools.image_gate import (
    append_image_asset_record,
    list_image_asset_records,
)


def test_user_feedback_persist_on_scope_accessor_path(tmp_path) -> None:
    scope = CompanionScope("tools-uf", "agent-1", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.companion_user_feedback_jsonl

    append_user_feedback_record(store, {"kind": "snapshot", "feedback_id": "fb-1"})

    raw = store.read_document_if_exists(rel)
    assert raw is not None
    assert "fb-1" in raw


def test_image_index_persist_on_scope_accessor_path(tmp_path) -> None:
    scope = CompanionScope("tools-img", "agent-1", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.generated_images_index_jsonl

    append_image_asset_record(store, {"asset_id": "img-a1", "path": "generated_images/a1.png"})

    raw = store.read_document_if_exists(rel)
    assert raw is not None
    rows = list_image_asset_records(store)
    assert len(rows) == 1
    assert rows[0]["asset_id"] == "img-a1"
    assert rel.endswith("index.jsonl")


def test_living_sphere_updates_read_on_scope_accessor_path(tmp_path) -> None:
    scope = CompanionScope("tools-ls", "agent-1", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.living_sphere_updates_jsonl
    line = (
        '{"update_id":"u1","created_at_utc":"2026-01-01T00:00:00+00:00",'
        '"change_request":"add a reading nook"}'
    )
    store.write_document(rel, line + "\n")

    updates = _read_all_updates(store)
    assert len(updates) == 1
    assert updates[0].update_id == "u1"
