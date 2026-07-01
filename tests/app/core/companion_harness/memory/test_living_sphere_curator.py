from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.living_sphere_curator import (
    compact_living_sphere_if_pending,
    wait_for_tool_background_before_living_sphere_compact,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_path_constants import (
    LIVING_SPHERE_MD_REL,
)
from app.living_sphere.models import (
    LivingSphereUpdate,
)
from app.living_sphere.seeding import seed_living_sphere_markdown


def test_compact_waits_for_tool_background_idle(tmp_path: Path) -> None:
    root = tmp_path / "ls-wait-bg"
    root.mkdir()
    store = MemoryStore(
        scope=CompanionScope("t", "a", str(root.resolve())),
        repository=None,
    )
    store.write_document(
        LIVING_SPHERE_MD_REL, seed_living_sphere_markdown()
    )
    ev = threading.Event()
    ev.clear()
    appended: list[str] = []

    def bg_append() -> None:
        time.sleep(0.15)
        u = LivingSphereUpdate(change_request="后台追加")
        store.append_jsonl_record(
            "living_sphere_updates.jsonl",
            u.model_dump(mode="json"),
        )
        appended.append(u.update_id)
        ev.set()

    threading.Thread(target=bg_append, daemon=True).start()
    wait_for_tool_background_before_living_sphere_compact(
        ev, scope_registry_key=store.scope.registry_key()
    )
    assert appended

    def fake_complete(msgs: list[dict[str, Any]], model_role: str) -> str:
        body = seed_living_sphere_markdown()
        return body.replace("氛围：", "氛围：后台，", 1)

    assert compact_living_sphere_if_pending(
        store, fake_complete, tool_bg_idle_event=ev
    )
