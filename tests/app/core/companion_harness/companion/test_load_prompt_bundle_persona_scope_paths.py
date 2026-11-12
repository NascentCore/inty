"""Smoke tests: load_prompt_bundle core persona paths use MemoryStoreScopePaths (#3413).

Generated entirely by Cursor agent.
"""

from __future__ import annotations

from pathlib import Path

from app.core.companion_harness.companion.models import ContextMeta, load_prompt_bundle
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)


def test_load_prompt_bundle_persona_reads_use_scope_path_accessors(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        scope=CompanionScope("bundle-scope", "agent-1", tmp_path.name),
        repository=None,
    )
    paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    store.write_document(paths.identity, "# Identity\nscope identity body\n")
    store.write_document(paths.soul, "# Soul\nscope soul body\n")
    store.write_document(paths.style_md, "# Style\nscope style body\n")
    store.write_document(paths.user_md, "# User\nscope user body\n")
    store.write_document(paths.memory_md, "# Memory\nscope memory body\n")
    store.write_document(paths.channels_md, "# Channels\nscope channels body\n")
    store.write_document(
        paths.companionship_md,
        "# 我们的关系\n\nscope companionship body\n",
    )

    bundle = load_prompt_bundle(store, meta=ContextMeta())

    assert "scope identity body" in bundle.identity
    assert "scope soul body" in bundle.soul
    assert "scope style body" in bundle.style_md
    assert "scope user body" in bundle.user_md
    assert "scope memory body" in bundle.memory_md
    assert "scope channels body" in bundle.channels_md
    assert "scope companionship body" in bundle.companionship_md
