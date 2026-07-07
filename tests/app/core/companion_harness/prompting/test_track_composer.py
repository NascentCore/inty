"""Tests for TrackPromptComposer and projection pipeline wrappers."""

from __future__ import annotations

from pathlib import Path

from app.core.companion_harness.companion.models import CompanionTurnTrack
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.retrieval import (
    RetrievalTier,
    select_slices_for_turn,
)
from app.core.companion_harness.prompting.bundle import PromptBundle
from app.core.companion_harness.prompting.track_composer import (
    TrackPromptComposer,
)


def test_retrieval_tier_enum_values() -> None:
    assert RetrievalTier.RESIDENT.value == "resident"


def test_select_slices_for_turn_returns_transcript_window(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        scope=CompanionScope("compose", "a", tmp_path.name),
        repository=None,
    )
    selection = select_slices_for_turn(
        track=CompanionTurnTrack.USER_CHAT,
        store=store,
        bundle=PromptBundle(identity="", soul="", user_md="", memory_md=""),
    )
    assert selection.transcript_window_spec == "CHAT_HISTORY.md"


def test_track_composer_wraps_openai_messages() -> None:
    composer = TrackPromptComposer()
    plan = composer.compose_from_openai_messages(
        [
            {"role": "system", "content": "hello"},
            {"role": "user", "content": "hi"},
        ],
        tools=(),
    )
    assert len(plan.messages) == 2
    assert plan.messages[-1].role.value == "user"
