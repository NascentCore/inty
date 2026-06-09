from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import pytest

from app.core.companion_harness.runtime.scope import CompanionScope
from app.core.companion_harness.memory.living_sphere_curator import (
    LivingSphereCuratorOutputRejected,
    compact_living_sphere_batch,
    compact_living_sphere_if_pending,
    living_sphere_curator_output_rejection_reason,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.living_sphere.models import LivingSphereUpdate
from app.living_sphere.seeding import LIVING_SPHERE_RELATIVE_PATH, seed_living_sphere_markdown


def _valid_md(suffix: str = "") -> str:
    base = seed_living_sphere_markdown()
    if suffix:
        return base.replace("氛围：", f"氛围：{suffix}，", 1)
    return base


def _idle_tool_bg() -> threading.Event:
    ev = threading.Event()
    ev.set()
    return ev


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
        return _valid_md("台灯")

    idle = _idle_tool_bg()
    assert compact_living_sphere_if_pending(store, fake_complete, tool_bg_idle_event=idle) is True
    assert "台灯" in store.read_document(LIVING_SPHERE_RELATIVE_PATH)
    state = json.loads(store.read_document(".companion_living_sphere_curator.json"))
    assert state["living_sphere_curated_through_update_id"] == u2.update_id
    assert compact_living_sphere_if_pending(store, fake_complete, tool_bg_idle_event=idle) is False


def test_curator_drains_more_than_batch_cap_without_skipping(tmp_path: Path) -> None:
    root = tmp_path / "ls-cap"
    root.mkdir()
    store = MemoryStore(
        scope=CompanionScope("t", "a", str(root.resolve())),
        repository=None,
    )
    store.write_document(LIVING_SPHERE_RELATIVE_PATH, seed_living_sphere_markdown())
    updates = [
        LivingSphereUpdate(change_request=f"变更-{i}") for i in range(25)
    ]
    for u in updates:
        store.append_jsonl_record(
            "living_sphere_updates.jsonl",
            u.model_dump(mode="json"),
        )
    calls = 0

    def fake_complete(msgs: list[dict[str, Any]], model_role: str) -> str:
        nonlocal calls
        calls += 1
        return _valid_md(f"batch-{calls}")

    idle = _idle_tool_bg()
    assert compact_living_sphere_if_pending(store, fake_complete, tool_bg_idle_event=idle) is True
    assert calls == 2
    state = json.loads(store.read_document(".companion_living_sphere_curator.json"))
    assert state["living_sphere_curated_through_update_id"] == updates[-1].update_id
    assert compact_living_sphere_if_pending(store, fake_complete, tool_bg_idle_event=idle) is False


def test_curator_rejects_bad_output_without_advancing_cursor(tmp_path: Path) -> None:
    root = tmp_path / "ls-reject"
    root.mkdir()
    store = MemoryStore(
        scope=CompanionScope("t", "a", str(root.resolve())),
        repository=None,
    )
    original = seed_living_sphere_markdown()
    store.write_document(LIVING_SPHERE_RELATIVE_PATH, original)
    u = LivingSphereUpdate(change_request="加绿植")
    store.append_jsonl_record(
        "living_sphere_updates.jsonl",
        u.model_dump(mode="json"),
    )

    def fake_complete(msgs: list[dict[str, Any]], model_role: str) -> str:
        return "too short"

    assert living_sphere_curator_output_rejection_reason("too short") is not None
    with pytest.raises(LivingSphereCuratorOutputRejected):
        compact_living_sphere_if_pending(
            store, fake_complete, tool_bg_idle_event=_idle_tool_bg()
        )
    assert store.read_document(LIVING_SPHERE_RELATIVE_PATH) == original
    raw = store.read_document_if_exists(".companion_living_sphere_curator.json")
    assert raw is None or "living_sphere_curated_through_update_id" not in raw


def test_curator_malformed_jsonl_line_raises(tmp_path: Path) -> None:
    root = tmp_path / "ls-bad-line"
    root.mkdir()
    store = MemoryStore(
        scope=CompanionScope("t", "a", str(root.resolve())),
        repository=None,
    )
    store.write_document(LIVING_SPHERE_RELATIVE_PATH, seed_living_sphere_markdown())
    good = LivingSphereUpdate(change_request="有效变更")
    store.write_document(
        "living_sphere_updates.jsonl",
        "not-json\n"
        + json.dumps(good.model_dump(mode="json"), ensure_ascii=False)
        + "\n",
    )

    def fake_complete(msgs: list[dict[str, Any]], model_role: str) -> str:
        return _valid_md("有效")

    with pytest.raises(json.JSONDecodeError):
        compact_living_sphere_if_pending(
            store, fake_complete, tool_bg_idle_event=_idle_tool_bg()
        )


def test_compact_living_sphere_batch_raises_on_rejected_output(tmp_path: Path) -> None:
    root = tmp_path / "ls-batch-reject"
    root.mkdir()
    store = MemoryStore(
        scope=CompanionScope("t", "a", str(root.resolve())),
        repository=None,
    )
    store.write_document(LIVING_SPHERE_RELATIVE_PATH, seed_living_sphere_markdown())
    batch = [LivingSphereUpdate(change_request="x")]

    def bad_complete(msgs: list[dict[str, Any]], model_role: str) -> str:
        return "# oops\n\nno markers"

    with pytest.raises(LivingSphereCuratorOutputRejected):
        compact_living_sphere_batch(store, batch, bad_complete)
