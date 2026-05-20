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


def test_proactive_chat_empty_transcript(tmp_path: Path) -> None:
    scope = CompanionScope("pc-empty", "a", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    store.write_document("transcript.jsonl", "")
    cfg = ProactiveChatConfig(min_transcript_lines=1)
    assert next_proactive_chat_wait_seconds(store, cfg) == 86400.0 * 365.0


def test_next_proactive_chat_wait_seconds_anchors_on_last_assistant_only(
    tmp_path: Path,
) -> None:
    """After proactive chat rows, scheduling uses last assistant + rhythm (not min_gap)."""
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
    cfg = ProactiveChatConfig(base_idle_sec=10.0, min_transcript_lines=2)
    now_past = t3 + timedelta(seconds=120)
    assert next_proactive_chat_wait_seconds(store, cfg, now=now_past) <= 0.0

    now_before_earliest = t3 + timedelta(seconds=1)
    wait = next_proactive_chat_wait_seconds(store, cfg, now=now_before_earliest)
    assert 0.0 < wait <= 20.0


def test_rhythm_ignores_proactive_user_gaps(tmp_path: Path) -> None:
    """Real-user gaps drive rhythm; proactive synthetic user rows are excluded."""
    scope = CompanionScope("pc-rhythm", "a", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(seconds=1)
    t2 = t1 + timedelta(seconds=50)
    t3 = t2 + timedelta(seconds=1)
    t4 = t3 + timedelta(seconds=80)
    t5 = t4 + timedelta(seconds=1)
    t6 = t5 + timedelta(seconds=1)
    t7 = t6 + timedelta(seconds=1)
    store.append_jsonl_record(
        "transcript.jsonl",
        {"role": "user", "content": "u0", "ts": t0.isoformat()},
    )
    store.append_jsonl_record(
        "transcript.jsonl",
        {"role": "assistant", "content": "a0", "ts": t1.isoformat()},
    )
    store.append_jsonl_record(
        "transcript.jsonl",
        {"role": "user", "content": "u1", "ts": t2.isoformat()},
    )
    store.append_jsonl_record(
        "transcript.jsonl",
        {"role": "assistant", "content": "a1", "ts": t3.isoformat()},
    )
    store.append_jsonl_record(
        "transcript.jsonl",
        {"role": "user", "content": "u2", "ts": t4.isoformat()},
    )
    store.append_jsonl_record(
        "transcript.jsonl",
        {"role": "assistant", "content": "a2", "ts": t5.isoformat()},
    )
    store.append_jsonl_record(
        "transcript.jsonl",
        {
            "role": "user",
            "content": "pc",
            "ts": t6.isoformat(),
            "proactive_chat": True,
        },
    )
    store.append_jsonl_record(
        "transcript.jsonl",
        {"role": "assistant", "content": "last", "ts": t7.isoformat()},
    )
    cfg = ProactiveChatConfig(base_idle_sec=30.0)
    wait = next_proactive_chat_wait_seconds(
        store, cfg, now=t7 + timedelta(seconds=1)
    )
    # median(real gaps 50,80)=65 → scaled=62.25; cap base*2=60
    assert 55.0 <= wait <= 65.0
