from __future__ import annotations

from pathlib import Path

from app.core.companion_harness.companion.ai_private_prompt import (
    append_ai_private_thought,
)
from app.core.companion_harness.companion.models import (
    AI_PRIVATE_SPLICE_MANIFEST_SOURCE,
    ChatMessage,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.transcript_ai_private import (
    dreaming_transcript_block,
)
from app.core.companion_harness.memory.memory_store import MemoryStore


def test_dreaming_transcript_block_hydrates_manifest_and_unconsumed(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        scope=CompanionScope("dream-ap", "a", tmp_path.name),
        repository=None,
    )
    thought = append_ai_private_thought(
        store, text="rolled monolog", after_user_msg_uuid=None
    )
    rows = [
        ChatMessage(
            role="user",
            content="hi",
            ts="2026-01-02T09:00:00+00:00",
            uuid="u1",
        ),
        ChatMessage(
            role="system",
            content="[ai_private_splice]",
            ts="2026-01-02T09:01:00+00:00",
            uuid="m1",
            source=AI_PRIVATE_SPLICE_MANIFEST_SOURCE,
            ai_private_thought_uuids=[thought.uuid],
        ),
    ]
    block = dreaming_transcript_block(store, rows, day_iso="2026-01-02")
    assert "Inner monolog (ai_private): rolled monolog" in block
    assert "[ai_private_splice]" not in block
    assert block.count("rolled monolog") == 1


def test_dreaming_transcript_block_skips_unconsumed_when_manifest_hydrated(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        scope=CompanionScope("dream-dedupe", "a", tmp_path.name),
        repository=None,
    )
    thought = append_ai_private_thought(
        store, text="already in manifest", after_user_msg_uuid=None
    )
    rows = [
        ChatMessage(
            role="system",
            content="[ai_private_splice]",
            ts="2026-01-02T09:01:00+00:00",
            uuid="m1",
            source=AI_PRIVATE_SPLICE_MANIFEST_SOURCE,
            ai_private_thought_uuids=[thought.uuid],
        ),
    ]
    block = dreaming_transcript_block(store, rows, day_iso="2026-01-02")
    assert "already in manifest" in block
    assert "--- Monolog (ai_private, unconsumed) ---" not in block
