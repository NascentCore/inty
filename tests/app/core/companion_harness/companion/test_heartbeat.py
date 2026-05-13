from __future__ import annotations

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
