from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

from app.core.agentic_kernel.companion.inner_tick_schedule import (
    inner_tick_enabled_from_env,
    next_inner_tick_wait_seconds,
)


def _write_transcript(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )


def test_inner_tick_env_unset_defaults_enabled() -> None:
    with patch.dict(os.environ, {}, clear=True):
        assert inner_tick_enabled_from_env() is True


def test_next_inner_tick_short_transcript_returns_poll_chunk(tmp_path: Path) -> None:
    root = tmp_path
    _write_transcript(
        root / "transcript.jsonl",
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
