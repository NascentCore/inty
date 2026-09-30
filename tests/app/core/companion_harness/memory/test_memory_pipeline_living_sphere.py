from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from app.core.companion_harness.companion.models import ChatMessage
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.dreaming_consolidation import (
    consolidate_memory_during_dreaming,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)
from app.living_sphere.models import LivingSphereUpdate
from app.living_sphere.seeding import seed_living_sphere_markdown
from app.utils.config import DreamingCuratorMode
from tests.app.core.companion_harness.companion.companion_scripted_llm import (
    UnusedLlmClient,
)


def _idle_tool_bg() -> threading.Event:
    ev = threading.Event()
    ev.set()
    return ev


def _seed_store(store: MemoryStore) -> None:
    paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    for name, body in (
        (paths.identity, "id\n"),
        (paths.soul, "soul\n"),
        (paths.style_md, "style\n"),
        (paths.user_md, "u\n"),
        (paths.memory_md, "m\n"),
        (paths.companionship_md, "companionship\n"),
    ):
        store.write_document(name, body)
    store.write_document(paths.living_sphere_md, seed_living_sphere_markdown())


def _valid_md() -> str:
    return seed_living_sphere_markdown().replace("氛围：", "氛围：合并，", 1)


def _dream_rows() -> list[ChatMessage]:
    return [
        ChatMessage(
            role="user",
            content="hi",
            ts="2026-01-02T09:00:00+00:00",
            uuid="u",
        ),
        ChatMessage(
            role="assistant",
            content="hello",
            ts="2026-01-02T09:01:00+00:00",
            uuid="a",
        ),
    ]


def test_dreaming_consolidation_compacts_living_sphere_when_pending(
    tmp_path: Path,
) -> None:
    root = tmp_path / "mp-ls"
    root.mkdir()
    store = MemoryStore(
        scope=CompanionScope("t", "a", str(root.resolve())),
        repository=None,
    )
    _seed_store(store)
    update = LivingSphereUpdate(change_request="窗边加绿植")
    paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    store.append_jsonl_record(
        paths.living_sphere_updates_jsonl,
        update.model_dump(mode="json"),
    )
    roles: list[str] = []

    def fake_complete(msgs: list[dict[str, Any]], model_role: str) -> str:
        roles.append(model_role)
        if model_role == "memory":
            return _valid_md()
        return "noop\n"

    assert (
        consolidate_memory_during_dreaming(
            store,
            _dream_rows(),
            DreamingCuratorMode.SEQUENTIAL,
            fake_complete,
            UnusedLlmClient(),
            langsmith_extra={},
            tool_bg_idle_event=_idle_tool_bg(),
        )
        is True
    )
    assert "memory" in roles
    assert "合并" in store.read_document(paths.living_sphere_md)
    state = json.loads(
        store.read_document(paths.living_sphere_curator_state_json)
    )
    assert state["living_sphere_curated_through_update_id"] == update.update_id


def test_dreaming_consolidation_skips_living_sphere_curator_without_pending(
    tmp_path: Path,
) -> None:
    root = tmp_path / "mp-ls-skip"
    root.mkdir()
    store = MemoryStore(
        scope=CompanionScope("t", "a", str(root.resolve())),
        repository=None,
    )
    _seed_store(store)
    paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    original = store.read_document(paths.living_sphere_md)

    def fake_complete(msgs: list[dict[str, Any]], model_role: str) -> str:
        return "noop\n"

    consolidate_memory_during_dreaming(
        store,
        _dream_rows(),
        DreamingCuratorMode.SEQUENTIAL,
        fake_complete,
        UnusedLlmClient(),
        langsmith_extra={},
        tool_bg_idle_event=_idle_tool_bg(),
    )
    assert store.read_document(paths.living_sphere_md) == original


def test_dreaming_consolidation_waits_for_tool_background_before_compact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """jsonl append on main thread; idle Event released from background (no cross-thread store)."""
    root = tmp_path / "mp-ls-bg"
    root.mkdir()
    store = MemoryStore(
        scope=CompanionScope("t", "a", str(root.resolve())),
        repository=None,
    )
    _seed_store(store)
    update = LivingSphereUpdate(change_request="tool_background 已写入")
    paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    store.append_jsonl_record(
        paths.living_sphere_updates_jsonl,
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

    consolidate_memory_during_dreaming(
        store,
        _dream_rows(),
        DreamingCuratorMode.SEQUENTIAL,
        fake_complete,
        UnusedLlmClient(),
        langsmith_extra={},
        tool_bg_idle_event=ev,
    )
    state = json.loads(
        store.read_document(paths.living_sphere_curator_state_json)
    )
    assert state["living_sphere_curated_through_update_id"] == update.update_id
    assert "合并" in store.read_document(paths.living_sphere_md)
