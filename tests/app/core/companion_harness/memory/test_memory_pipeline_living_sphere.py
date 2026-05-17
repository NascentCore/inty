from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_pipeline import (
    MemoryPipelineConfig,
    memory_update_after_turn,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from living_sphere.models import LivingSphereUpdate
from living_sphere.seeding import LIVING_SPHERE_RELATIVE_PATH, seed_living_sphere_markdown


def _seed_pipeline_store(store: MemoryStore) -> None:
    for name, body in (
        ("IDENTITY.md", "id\n"),
        ("SOUL.md", "soul\n"),
        ("STYLE.md", "style\n"),
        ("USER.md", "u\n"),
        ("MEMORY.md", "m\n"),
    ):
        store.write_document(name, body)
    store.write_document(LIVING_SPHERE_RELATIVE_PATH, seed_living_sphere_markdown())


def test_memory_pipeline_compacts_living_sphere_when_pending(
    tmp_path: Path,
) -> None:
    root = tmp_path / "mp-ls"
    root.mkdir()
    store = MemoryStore(
        scope=CompanionScope("t", "a", str(root.resolve())),
        repository=None,
    )
    _seed_pipeline_store(store)
    update = LivingSphereUpdate(change_request="窗边加绿植")
    store.append_jsonl_record(
        "living_sphere_updates.jsonl",
        update.model_dump(mode="json"),
    )
    roles: list[str] = []

    def fake_complete(msgs: list[dict[str, Any]], model_role: str) -> str:
        roles.append(model_role)
        if model_role == "memory":
            return "# LIVING SPHERE\n\n含绿植\n"
        return "noop\n"

    cfg = MemoryPipelineConfig(memory_update_every_n_turns=999)
    memory_update_after_turn(store, "hi", "hello", fake_complete, cfg)
    assert "memory" in roles
    assert "含绿植" in store.read_document(LIVING_SPHERE_RELATIVE_PATH)
    state = json.loads(store.read_document(".companion_memory_pipeline.json"))
    assert state["living_sphere_curated_through_update_id"] == update.update_id


def test_memory_pipeline_skips_living_sphere_curator_without_pending(
    tmp_path: Path,
) -> None:
    root = tmp_path / "mp-ls-skip"
    root.mkdir()
    store = MemoryStore(
        scope=CompanionScope("t", "a", str(root.resolve())),
        repository=None,
    )
    _seed_pipeline_store(store)
    original = store.read_document(LIVING_SPHERE_RELATIVE_PATH)
    roles: list[str] = []

    def fake_complete(msgs: list[dict[str, Any]], model_role: str) -> str:
        roles.append(model_role)
        return "noop\n"

    cfg = MemoryPipelineConfig(memory_update_every_n_turns=999)
    memory_update_after_turn(store, "hi", "hello", fake_complete, cfg)
    assert "memory" not in roles
    assert store.read_document(LIVING_SPHERE_RELATIVE_PATH) == original
