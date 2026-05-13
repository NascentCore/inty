"""Workspace seeding helpers for harness demo."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.companion_harness.memory.memory_registry import get_memory_store
from app.core.companion_harness.memory.scope import CompanionScope

from experimental.harness_seeding_demo.workspace_setup import seed_memory_store_from_directory


def test_seed_memory_store_rejects_missing_seed_dir(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    scope = CompanionScope("u", "c", "chat-missing")
    with pytest.raises(FileNotFoundError):
        seed_memory_store_from_directory(missing, scope)


def test_seed_memory_store_populates_store(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    seed = repo / "experimental/harness_seeding_demo/seeds/baseline"
    scope = CompanionScope("harness_user_x", "demo_companion", "demo_chat")
    seed_memory_store_from_directory(seed, scope)
    store = get_memory_store(scope, dsn="")
    assert store.read_document_if_exists("SOUL.md")
    assert store.read_document_if_exists("transcript.jsonl") is not None
