"""Tests for memory retrieval slice selection."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    transcript_relative_path_for_turn_persistence,
)
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


@pytest.mark.parametrize(
    "track, expected_rel",
    [
        (CompanionTurnTrack.USER_CHAT, DEFAULT_MEMORY_STORE_SCOPE_PATHS.transcript),
        (
            CompanionTurnTrack.USER_CHAT_BOOTSTRAP,
            DEFAULT_MEMORY_STORE_SCOPE_PATHS.transcript,
        ),
        (
            CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING,
            DEFAULT_MEMORY_STORE_SCOPE_PATHS.transcript,
        ),
        (
            CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT,
            DEFAULT_MEMORY_STORE_SCOPE_PATHS.transcript,
        ),
        (
            CompanionTurnTrack.INNER_TICK_SCHEDULED,
            DEFAULT_MEMORY_STORE_SCOPE_PATHS.transcript,
        ),
        (
            CompanionTurnTrack.INNER_TICK_MONOLOG,
            DEFAULT_MEMORY_STORE_SCOPE_PATHS.transcript_inner_tick,
        ),
        (
            CompanionTurnTrack.INNER_TICK_AUTONOMY,
            DEFAULT_MEMORY_STORE_SCOPE_PATHS.transcript_inner_tick,
        ),
    ],
)
def test_transcript_relative_path_for_turn_persistence_matches_scope_accessors(
    track: CompanionTurnTrack,
    expected_rel: str,
) -> None:
    assert (
        transcript_relative_path_for_turn_persistence(track=track)
        == expected_rel
    )
