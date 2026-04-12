from __future__ import annotations

from pathlib import Path

from app.core.agentic_kernel.companion.inner_tick import next_companion_inner_tick_wait_seconds
from app.core.agentic_kernel.companion.memory_store import MemoryStore


def _minimal_transcript_assistant_last(store: MemoryStore, rel: str) -> None:
    body = (
        '{"role":"user","content":"hi","ts":"2026-01-01T00:00:00Z"}\n'
        '{"role":"assistant","content":"ok","ts":"2026-01-01T00:00:01Z"}\n'
    )
    store.write_document(rel, body)


def test_next_inner_tick_first_after_user_delay(tmp_path: Path) -> None:
    root = tmp_path
    store = MemoryStore(workspace_root=root, repository=None, mirror_to_files=True)
    rel = "transcript.jsonl"
    _minimal_transcript_assistant_last(store, rel)
    t0 = 1000.0
    w = next_companion_inner_tick_wait_seconds(
        root,
        store,
        last_inner_fire_monotonic=None,
        last_chat_turn_complete_monotonic=t0,
        first_after_user_seconds=30.0,
        min_gap_seconds=120.0,
        min_transcript_messages=2,
        poll_cap_seconds=90.0,
        blocked_max_seconds=60.0,
        now_monotonic=t0 + 5.0,
    )
    assert 24.9 < w < 25.1


def test_next_inner_tick_after_inner_uses_min_gap(tmp_path: Path) -> None:
    root = tmp_path
    store = MemoryStore(workspace_root=root, repository=None, mirror_to_files=True)
    rel = "transcript.jsonl"
    _minimal_transcript_assistant_last(store, rel)
    last_inner = 2000.0
    w = next_companion_inner_tick_wait_seconds(
        root,
        store,
        last_inner_fire_monotonic=last_inner,
        last_chat_turn_complete_monotonic=1900.0,
        first_after_user_seconds=15.0,
        min_gap_seconds=100.0,
        min_transcript_messages=2,
        poll_cap_seconds=90.0,
        blocked_max_seconds=60.0,
        now_monotonic=last_inner + 20.0,
    )
    assert 79.9 < w < 80.1
