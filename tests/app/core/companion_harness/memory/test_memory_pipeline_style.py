from __future__ import annotations

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
    ("style_every_n", "expect_style_call"),
    (
        (1, True),
        (999, False),
    ),
)
def test_memory_pipeline_style_curator_interval(
    tmp_path: Path, style_every_n: int, expect_style_call: bool
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

    cfg = MemoryPipelineConfig(
        day_summary_disabled=True,
        memory_update_every_n_turns=999,
        user_update_every_n_turns=999,
        style_update_every_n_turns=style_every_n,
        soul_update_every_n_turns=999,
    )
    memory_update_after_turn(
        store,
        "hello",
        "hi there",
        fake_complete,
        cfg,
    )
    if expect_style_call:
        assert "style" in roles
        assert "updated style body" in store.read_document("STYLE.md")
    else:
        assert "style" not in roles
        assert store.read_document("STYLE.md") == "style original\n"


def test_memory_pipeline_style_skipped_when_disabled(tmp_path: Path) -> None:
    root = tmp_path / "mp-style-off"
    root.mkdir()
    store = MemoryStore(
        scope=CompanionScope("t2", "a", str(root.resolve())),
        repository=None,
    )
    _seed_pipeline_store(store)

    def fake_complete(msgs: list[dict[str, Any]], model_role: str) -> str:
        raise AssertionError(f"complete_fn should not run when disabled: {model_role}")

    cfg = MemoryPipelineConfig(
        day_summary_disabled=True,
        memory_update_every_n_turns=999,
        user_update_every_n_turns=999,
        style_update_every_n_turns=1,
        style_update_disabled=True,
        soul_update_every_n_turns=999,
    )
    memory_update_after_turn(store, "a", "b", fake_complete, cfg)
    assert store.read_document("STYLE.md") == "style original\n"
