"""Tests for memory retrieval slice selection."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.companion_harness.companion.models import CompanionTurnTrack
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)
from app.core.companion_harness.memory.retrieval import select_slices_for_turn
from app.core.companion_harness.prompting.bundle import PromptBundle


@pytest.mark.parametrize(
    "track",
    list(CompanionTurnTrack),
)
def test_select_slices_for_turn_uses_chat_history_window_spec(
    tmp_path: Path,
    track: CompanionTurnTrack,
) -> None:
    store = MemoryStore(
        scope=CompanionScope(
            "retrieval",
            "a",
            str(tmp_path.resolve()),
        ),
        repository=None,
    )
    bundle = PromptBundle(
        identity="id",
        soul="soul",
        user_md="user",
        memory_md="mem",
    )
    selection = select_slices_for_turn(
        track=track,
        store=store,
        bundle=bundle,
    )
    assert selection.resident_paths == ()
    assert (
        selection.transcript_window_spec
        == DEFAULT_MEMORY_STORE_SCOPE_PATHS.chat_history_md
    )
