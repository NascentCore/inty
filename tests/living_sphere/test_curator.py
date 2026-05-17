from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from living_sphere.curator import compact_living_sphere_if_pending
from living_sphere.models import LivingSphereUpdate
from living_sphere.seeding import LIVING_SPHERE_RELATIVE_PATH, seed_living_sphere_markdown


def test_curator_merges_pending_into_living_sphere_md(tmp_path: Path) -> None:
    root = tmp_path / "ls-curator"
    root.mkdir()
    store = MemoryStore(
        scope=CompanionScope("t", "a", str(root.resolve())),
        repository=None,
    )
    store.write_document(LIVING_SPHERE_RELATIVE_PATH, seed_living_sphere_markdown())
    u1 = LivingSphereUpdate(change_request="在书架旁加一盏台灯")
    u2 = LivingSphereUpdate(change_request="默认位置改到书架旁")
    for u in (u1, u2):
        store.append_jsonl_record(
            "living_sphere_updates.jsonl",
            u.model_dump(mode="json"),
        )

    def fake_complete(msgs: list[dict[str, Any]], model_role: str) -> str:
        assert model_role == "memory"
        return "# LIVING SPHERE\n\nmerged with 台灯\n"

    assert compact_living_sphere_if_pending(store, fake_complete) is True
    assert "台灯" in store.read_document(LIVING_SPHERE_RELATIVE_PATH)
    state = json.loads(store.read_document(".companion_memory_pipeline.json"))
    assert state["living_sphere_curated_through_update_id"] == u2.update_id

    assert compact_living_sphere_if_pending(store, fake_complete) is False
