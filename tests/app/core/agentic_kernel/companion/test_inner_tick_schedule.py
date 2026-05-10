from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

from app.core.agentic_kernel.companion.memory_registry import get_memory_store
from app.core.agentic_kernel.companion.inner_tick_schedule import (
    InnerTickScheduleOverrides,
    inner_tick_enabled_from_env,
    next_inner_tick_wait_seconds,
)


def _write_transcript_store(root: Path, rows: list[dict[str, object]]) -> None:
    body = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n"
    get_memory_store(root).write_document("transcript.jsonl", body)


def test_inner_tick_env_unset_defaults_enabled() -> None:
    with patch.dict(os.environ, {}, clear=True):
        assert inner_tick_enabled_from_env() is True


def test_next_inner_tick_short_transcript_returns_poll_chunk(tmp_path: Path) -> None:
    root = tmp_path
    _write_transcript_store(
        root,
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
        w = next_inner_tick_wait_seconds(root, last_inner_fire_monotonic=None)
    assert 0.0 < w < 86400.0 * 10


def test_next_inner_tick_overrides_enabled_false_disables(tmp_path: Path) -> None:
    root = tmp_path
    _write_transcript_store(
        root,
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
        root,
        last_inner_fire_monotonic=None,
        overrides=InnerTickScheduleOverrides(enabled=False),
    )
    assert w >= 86400.0 * 300
