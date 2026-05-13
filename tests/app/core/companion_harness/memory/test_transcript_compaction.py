from __future__ import annotations

from pathlib import Path

from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.transcript_compaction import (
    COMPACTION_SYSTEM_TAG,
    CompactionConfig,
    CompactionState,
    ConversationCompactor,
    load_compaction_state_from_store,
    save_compaction_state_to_store,
    transcript_rows_to_openai_dialogue,
)
from app.core.companion_harness.contracts.models import ChatMessage


def test_transcript_rows_to_openai_dialogue_includes_system() -> None:
    rows = [
        ChatMessage(role="user", content="hi", ts="2026-01-01T00:00:00Z"),
        ChatMessage(role="system", content="x", ts="2026-01-01T00:01:00Z"),
        ChatMessage(role="assistant", content="yo", ts="2026-01-01T00:02:00Z"),
    ]
    out = transcript_rows_to_openai_dialogue(rows)
    assert out == [
        {"role": "user", "content": "hi"},
        {"role": "system", "content": "x"},
        {"role": "assistant", "content": "yo"},
    ]


def test_compaction_state_roundtrip_via_memory_store(tmp_path: Path) -> None:
    from app.core.companion_harness.memory.scope import CompanionScope

    store = MemoryStore(
        scope=CompanionScope("tc", "a", tmp_path.name),
        repository=None,
    )
    rel = ".companion_context_compaction_state.json"
    state = CompactionState(
        running_summary="a",
        episodic_memory=[],
        semantic_memory=[],
        compaction_count=1,
    )
    save_compaction_state_to_store(store, rel, state)
    loaded = load_compaction_state_from_store(store, rel)
    assert loaded is not None
    assert loaded.running_summary == "a"
    assert loaded.compaction_count == 1


def test_maybe_compact_inserts_snapshot(tmp_path) -> None:
    compactor = ConversationCompactor(
        CompactionConfig(
            max_context_chars=420,
            keep_recent_messages=4,
            max_messages_per_episode=4,
            max_episodic_entries=20,
            max_semantic_entries=20,
            summary_max_chars=600,
            retrieval_episode_count=4,
            retrieval_semantic_count=6,
            retrieval_open_loop_count=4,
        )
    )
    messages = [
        {"role": "system", "content": "You are a caring AI companion."},
        *[
            pair
            for i in range(8)
            for pair in (
                {
                    "role": "user",
                    "content": f"Turn {i}: I am feeling stressed and I like jazz. Please help me process this tonight.",
                },
                {
                    "role": "assistant",
                    "content": f"Turn {i}: I hear you and I will stay with you. Please help me process this tonight.",
                },
            )
        ],
    ]
    outcome = compactor.maybe_compact(messages=messages, turn=9)
    assert outcome.did_compact is True
    assert outcome.approx_chars_after < outcome.approx_chars_before
    snap = [
        m
        for m in outcome.messages
        if m["role"] == "system"
        and str(m.get("content", "")).startswith(COMPACTION_SYSTEM_TAG)
    ]
    assert len(snap) == 1
