"""Regression: path-key vs scope-key MemoryStore must be the same object when DSN-backed."""

from __future__ import annotations

from pathlib import Path

from app.core.agentic_kernel.companion.memory_registry import (
    get_memory_store,
    shutdown_all_memory_stores,
    shutdown_memory_store,
)


def test_get_memory_store_path_key_aliases_scope_key_with_dsn(tmp_path: Path) -> None:
    try:
        root = tmp_path / "u1" / "a1" / "c1"
        root.mkdir(parents=True)
        dsn = "postgresql://127.0.0.1:5432/none"
        scoped = get_memory_store(
            root,
            dsn=dsn,
            user_id="u1",
            companion_id="a1",
            chat_id="c1",
        )
        by_path = get_memory_store(root)
        assert by_path is scoped
        assert by_path.uses_repository_without_scope_disk is True
    finally:
        shutdown_all_memory_stores()


def test_shutdown_memory_store_evicts_path_and_scope_keys(tmp_path: Path) -> None:
    try:
        root = tmp_path / "u2" / "a2" / "c2"
        root.mkdir(parents=True)
        dsn = "postgresql://127.0.0.1:5432/none"
        s = get_memory_store(
            root,
            dsn=dsn,
            user_id="u2",
            companion_id="a2",
            chat_id="c2",
        )
        shutdown_memory_store(
            root,
            user_id="u2",
            companion_id="a2",
            chat_id="c2",
        )
        s2 = get_memory_store(
            root,
            dsn=dsn,
            user_id="u2",
            companion_id="a2",
            chat_id="c2",
        )
        assert s2 is not s
    finally:
        shutdown_all_memory_stores()
