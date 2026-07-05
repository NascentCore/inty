from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_path_constants import (
    CONTEXT_JSON_REL,
    TRANSCRIPT_JSONL_REL,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.inner_tick_schedule import (
    InnerTickScheduleOverrides,
    inner_tick_enabled_from_env,
    next_inner_tick_wait_seconds,
    transcript_tail_message_uuid,
)


def _write_transcript_store(
    scope: CompanionScope, rows: list[dict[str, object]]
) -> MemoryStore:
    body = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n"
    st = MemoryStore(scope=scope, repository=None)
    st.write_document(TRANSCRIPT_JSONL_REL, body)
    return st


def test_inner_tick_env_unset_defaults_enabled() -> None:
    with patch.dict(os.environ, {}, clear=True):
        assert inner_tick_enabled_from_env() is True


def test_next_inner_tick_short_transcript_returns_poll_chunk(
    tmp_path: Path,
) -> None:
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
        w = next_inner_tick_wait_seconds(
            store,
            last_inner_fire_monotonic=None,
            last_monolog_transcript_line_count=None,
        )
    assert 0.0 < w < 86400.0 * 10


def test_next_inner_tick_overrides_enabled_false_disables(
    tmp_path: Path,
) -> None:
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
        last_monolog_transcript_line_count=None,
        overrides=InnerTickScheduleOverrides(enabled=False),
    )
    assert w >= 86400.0 * 300


def test_next_inner_tick_incomplete_bootstrap_phase_disables(
    tmp_path: Path,
) -> None:
    sc = CompanionScope("it", "a", f"boot-{tmp_path.name}")
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
    store.write_document(
        CONTEXT_JSON_REL,
        json.dumps(
            {
                "context_mode": "unspecific",
                "workspace_bootstrap_user_interactive_completed": False,
            },
            ensure_ascii=False,
        ),
    )
    w = next_inner_tick_wait_seconds(
        store,
        last_inner_fire_monotonic=None,
        last_monolog_transcript_line_count=None,
    )
    assert w >= 86400.0 * 300


def test_next_inner_tick_skips_when_transcript_unchanged(
    tmp_path: Path,
) -> None:
    sc = CompanionScope("it", "a", f"unchanged-{tmp_path.name}")
    rows = [
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
    ]
    store = _write_transcript_store(sc, rows)
    w = next_inner_tick_wait_seconds(
        store,
        last_inner_fire_monotonic=0.0,
        last_monolog_transcript_line_count=len(rows),
    )
    assert w >= 86400.0 * 300


def test_transcript_tail_message_uuid_returns_last_business_row(
    tmp_path: Path,
) -> None:
    sc = CompanionScope("it", "a", f"tail-{tmp_path.name}")
    store = _write_transcript_store(
        sc,
        [
            {
                "role": "user",
                "content": "hi",
                "ts": "2026-01-01T00:00:00+00:00",
                "uuid": "user-1",
            },
            {
                "role": "assistant",
                "content": "yo",
                "ts": "2026-01-01T00:00:01+00:00",
                "uuid": "assistant-tail",
            },
            {
                "role": "user",
                "content": "",
                "ts": "2026-01-01T00:00:02+00:00",
                "uuid": "presence-tail",
                "presence": "repl_online",
            },
        ],
    )
    assert transcript_tail_message_uuid(store) == "assistant-tail"


def test_transcript_tail_message_uuid_empty_transcript(tmp_path: Path) -> None:
    sc = CompanionScope("it", "a", f"empty-{tmp_path.name}")
    store = MemoryStore(scope=sc, repository=None)
    assert transcript_tail_message_uuid(store) is None
