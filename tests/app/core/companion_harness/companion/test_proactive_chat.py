"""Tests for proactive chat scheduling (``proactive_chat.py``)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.companion_harness.companion.proactive_chat import (
    ProactiveChatConfig,
    next_proactive_chat_wait_seconds,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore


def test_proactive_chat_disabled(tmp_path: Path) -> None:
    cfg = ProactiveChatConfig(enabled=False)
    scope = CompanionScope("pc-off", "a", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    store.append_jsonl_record("transcript.jsonl", {"role": "user", "content": "hi", "ts": "2026-01-01T00:00:00Z"})
    store.append_jsonl_record("transcript.jsonl", {"role": "assistant", "content": "yo", "ts": "2026-01-01T00:00:01Z"})
    assert next_proactive_chat_wait_seconds(store, cfg) == 86400.0 * 365.0


def test_proactive_chat_empty_transcript(tmp_path: Path) -> None:
    scope = CompanionScope("pc-empty", "a", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    store.write_document("transcript.jsonl", "")
    cfg = ProactiveChatConfig(enabled=True, min_transcript_lines=1)
    assert next_proactive_chat_wait_seconds(store, cfg) == 86400.0 * 365.0


def test_next_proactive_chat_wait_seconds_successive_proactive_after_proactive_turn(
    tmp_path: Path,
) -> None:
    """After proactive chat (synthetic user + assistant), scheduling must not stick until real user speaks."""
    scope = CompanionScope("pc-gap", "a", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(seconds=30)
    t2 = t1 + timedelta(seconds=5)
    t3 = t2 + timedelta(seconds=5)
    store.append_jsonl_record(
        "transcript.jsonl",
        {"role": "user", "content": "real user", "ts": t0.isoformat()},
    )
    store.append_jsonl_record(
        "transcript.jsonl",
        {"role": "assistant", "content": "reply", "ts": t1.isoformat()},
    )
    store.append_jsonl_record(
        "transcript.jsonl",
        {
            "role": "user",
            "content": "[SYSTEM PROACTIVE CHAT]",
            "ts": t2.isoformat(),
            "proactive_chat": True,
        },
    )
    store.append_jsonl_record(
        "transcript.jsonl",
        {"role": "assistant", "content": "proactive reply", "ts": t3.isoformat()},
    )
    cfg = ProactiveChatConfig(
        enabled=True,
        base_idle_sec=10.0,
        min_gap_sec=30.0,
        min_transcript_lines=2,
    )
    now_past = t3 + timedelta(seconds=120)
    assert next_proactive_chat_wait_seconds(store, cfg, now=now_past) <= 0.0

    now_before_earliest = t3 + timedelta(seconds=1)
    wait = next_proactive_chat_wait_seconds(store, cfg, now=now_before_earliest)
    assert 0.0 < wait <= 30.0
