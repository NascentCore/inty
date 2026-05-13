from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from app.core.companion_harness.memory.memory_registry import get_memory_store
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.heartbeat import HeartbeatConfig, next_heartbeat_wait_seconds


def test_heartbeat_disabled(tmp_path: Path) -> None:
    cfg = HeartbeatConfig(enabled=False)
    store = MemoryStore(
        scope=CompanionScope("hb", "a", tmp_path.name),
        repository=None,
    )
    assert next_heartbeat_wait_seconds(store, cfg) == 86400.0 * 365.0


def test_heartbeat_empty_transcript(tmp_path: Path) -> None:
    sc = CompanionScope("hb", "a", f"e-{tmp_path.name}")
    store = get_memory_store(sc, dsn="")
    store.write_document("transcript.jsonl", "")
    cfg = HeartbeatConfig(enabled=True, min_transcript_lines=1)
    assert next_heartbeat_wait_seconds(store, cfg) == 86400.0 * 365.0


_NEVER = 86400.0 * 365.0


def test_next_heartbeat_wait_seconds_successive_proactive_after_heartbeat_turn(
    tmp_path: Path,
) -> None:
    """After a proactive heartbeat (heartbeat user + assistant), scheduling must not stick at _NEVER until a real user speaks."""
    sc = CompanionScope("hb", "a", f"succ-{tmp_path.name}")
    store = get_memory_store(sc, dsn="")
    t0 = "2026-01-01T10:00:00+00:00"
    t1 = "2026-01-01T10:00:10+00:00"
    t2 = "2026-01-01T10:05:00+00:00"
    t3 = "2026-01-01T10:05:05+00:00"
    rows = [
        {"role": "user", "content": "hi", "ts": t0},
        {"role": "assistant", "content": "hello", "ts": t1},
        {"role": "user", "content": "[SYSTEM HEARTBEAT]", "ts": t2, "heartbeat": True},
        {"role": "assistant", "content": "proactive reply", "ts": t3},
    ]
    store.write_document("transcript.jsonl", "\n".join(json.dumps(r) for r in rows))
    cfg = HeartbeatConfig(
        enabled=True,
        min_transcript_lines=0,
        base_idle_sec=30.0,
        min_gap_sec=60.0,
    )
    # Earliest = max(last_asst + rhythm, last_hb + min_gap) = max(10:05:35, 10:06:00) = 10:06:00 (rhythm uses base: only one user-user gap).
    now_past = datetime.fromisoformat("2026-01-01T10:06:30+00:00")
    assert next_heartbeat_wait_seconds(store, cfg, now=now_past) <= 0.0

    now_before_earliest = datetime.fromisoformat("2026-01-01T10:05:06+00:00")
    w = next_heartbeat_wait_seconds(store, cfg, now=now_before_earliest)
    assert w < _NEVER / 2
    assert 0.0 < w <= 60.0
