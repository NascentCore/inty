from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_pipeline import (
    MemoryPipelineConfig,
    memory_update_after_turn,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from living_sphere.models import LivingSphereUpdate
from living_sphere.seeding import LIVING_SPHERE_RELATIVE_PATH, seed_living_sphere_markdown


def _idle_tool_bg() -> threading.Event:
    ev = threading.Event()
    ev.set()
    return ev


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


def _valid_md() -> str:
    return seed_living_sphere_markdown().replace("氛围：", "氛围：合并，", 1)


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
            return _valid_md()
        return "noop\n"

    cfg = MemoryPipelineConfig(memory_update_every_n_turns=999)
    memory_curation = memory_update_after_turn(
        store, "hi", "hello", fake_complete, cfg, tool_bg_idle_event=_idle_tool_bg()
    )
    assert "memory" in roles
    assert "合并" in store.read_document(LIVING_SPHERE_RELATIVE_PATH)
    state = json.loads(store.read_document(".companion_memory_pipeline.json"))
    assert state["living_sphere_curated_through_update_id"] == update.update_id
    assert memory_curation is False


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
    memory_update_after_turn(
        store, "hi", "hello", fake_complete, cfg, tool_bg_idle_event=_idle_tool_bg()
    )
    assert "memory" not in roles
    assert store.read_document(LIVING_SPHERE_RELATIVE_PATH) == original


def test_memory_update_waits_for_tool_background_before_compact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """jsonl append on main thread; idle Event released from background (no cross-thread store)."""
    root = tmp_path / "mp-ls-bg"
    root.mkdir()
    store = MemoryStore(
        scope=CompanionScope("t", "a", str(root.resolve())),
        repository=None,
    )
    _seed_pipeline_store(store)
    update = LivingSphereUpdate(change_request="tool_background 已写入")
    store.append_jsonl_record(
        "living_sphere_updates.jsonl",
        update.model_dump(mode="json"),
    )
    ev = threading.Event()
    ev.clear()
    monkeypatch.setattr(
        "app.core.companion_harness.memory.living_sphere_curator._tool_bg_idle_wait_timeout_sec",
        lambda: 2.0,
    )

    def release_idle() -> None:
        time.sleep(0.05)
        ev.set()

    threading.Thread(target=release_idle, daemon=True).start()

    def fake_complete(msgs: list[dict[str, Any]], model_role: str) -> str:
        if model_role == "memory":
            return _valid_md()
        return "noop\n"

    memory_update_after_turn(
        store,
        "hi",
        "hello",
        fake_complete,
        MemoryPipelineConfig(memory_update_every_n_turns=999),
        tool_bg_idle_event=ev,
    )
    state = json.loads(store.read_document(".companion_memory_pipeline.json"))
    assert state["living_sphere_curated_through_update_id"] == update.update_id
    assert "合并" in store.read_document(LIVING_SPHERE_RELATIVE_PATH)
