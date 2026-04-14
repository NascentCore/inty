from __future__ import annotations

from pathlib import Path

from app.core.agentic_kernel.companion.memory_registry import get_memory_store
from app.core.agentic_kernel.companion.heartbeat import HeartbeatConfig, next_heartbeat_wait_seconds


def test_heartbeat_disabled(tmp_path: Path) -> None:
    cfg = HeartbeatConfig(enabled=False)
    assert next_heartbeat_wait_seconds(tmp_path, cfg) == 86400.0 * 365.0


def test_heartbeat_empty_transcript(tmp_path: Path) -> None:
    root = tmp_path
    root.mkdir(exist_ok=True)
    get_memory_store(root).write_document("transcript.jsonl", "")
    cfg = HeartbeatConfig(enabled=True, min_transcript_lines=1)
    assert next_heartbeat_wait_seconds(root, cfg) == 86400.0 * 365.0
