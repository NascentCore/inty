from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.inner_tick_schedule import (
    InnerTickScheduleOverrides,
    inner_tick_enabled_from_env,
    next_inner_tick_wait_seconds,
)


def _write_transcript_store(scope: CompanionScope, rows: list[dict[str, object]]) -> MemoryStore:
    body = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n"
    st = MemoryStore(scope=scope, repository=None)
    st.write_document("transcript.jsonl", body)
    return st


def test_inner_tick_env_unset_defaults_enabled() -> None:
    with patch.dict(os.environ, {}, clear=True):
        assert inner_tick_enabled_from_env() is True


def test_next_inner_tick_short_transcript_returns_poll_chunk(tmp_path: Path) -> None:
    sc = CompanionScope("it", "a", f"short-{tmp_path.name}")
    store = _write_transcript_store(
        sc,
        [
            {
                "role": "user",
                "content": "hi",
                "ts": "2026-01-01T00:00:00+00:00",
                "uuid": "a",
            },
        ],
    )
    with patch.dict(os.environ, {}, clear=True):
        w = next_inner_tick_wait_seconds(store, last_inner_fire_monotonic=None)
    assert 0.0 < w < 86400.0 * 10


def test_next_inner_tick_overrides_enabled_false_disables(tmp_path: Path) -> None:
    sc = CompanionScope("it", "a", f"ov-{tmp_path.name}")
    store = _write_transcript_store(
        sc,
        [
            {
                "role": "user",
                "content": "hi",
                "ts": "2026-01-01T00:00:00+00:00",
                "uuid": "a",
            },
            {
                "role": "assistant",
                "content": "yo",
                "ts": "2026-01-01T00:00:01+00:00",
                "uuid": "b",
            },
        ],
    )
    w = next_inner_tick_wait_seconds(
        store,
        last_inner_fire_monotonic=None,
        overrides=InnerTickScheduleOverrides(enabled=False),
    )
    assert w >= 86400.0 * 300
