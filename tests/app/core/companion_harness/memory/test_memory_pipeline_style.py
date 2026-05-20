from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import pytest

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_pipeline import (
    MemoryPipelineConfig,
    memory_update_after_turn,
)
from app.core.companion_harness.memory.memory_store import MemoryStore


def _seed_pipeline_store(store: MemoryStore) -> None:
    for name, body in (
        ("IDENTITY.md", "id\n"),
        ("SOUL.md", "soul\n"),
        ("STYLE.md", "style original\n"),
        ("USER.md", "u\n"),
        ("MEMORY.md", "m\n"),
    ):
        store.write_document(name, body)


@pytest.mark.parametrize(
    ("memory_update_every_n", "expect_style_call"),
    (
        (1, True),
        (999, False),
    ),
)
def test_memory_pipeline_style_curator_interval(
    tmp_path: Path, memory_update_every_n: int, expect_style_call: bool
) -> None:
    root = tmp_path / "mp-style"
    root.mkdir()
    store = MemoryStore(
        scope=CompanionScope("t", "a", str(root.resolve())),
        repository=None,
    )
    _seed_pipeline_store(store)

    roles: list[str] = []

    def fake_complete(msgs: list[dict[str, Any]], model_role: str) -> str:
        roles.append(model_role)
        if model_role == "style":
            return "# 沟通风格\n\nupdated style body\n"
        return "noop\n"

    cfg = MemoryPipelineConfig(memory_update_every_n_turns=memory_update_every_n)
    idle = threading.Event()
    idle.set()
    memory_update_after_turn(
        store,
        "hello",
        "hi there",
        fake_complete,
        cfg,
        tool_bg_idle_event=idle,
    )
    if expect_style_call:
        assert "style" in roles
        assert "updated style body" in store.read_document("STYLE.md")
    else:
        assert "style" not in roles
        assert store.read_document("STYLE.md") == "style original\n"
