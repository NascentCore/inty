from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.inner_tick_schedule import (
    InnerTickScheduleOverrides,
    inner_tick_enabled_from_env,
    maintenance_due_offline,
    next_inner_tick_wait_seconds,
    transcript_tail_message_uuid,
)

_USER_ROW = {
    "role": "user",
    "content": "hi",
    "ts": "2026-01-01T00:00:00+00:00",
    "uuid": "u",
}
_ASSISTANT_ROW = {
    "role": "assistant",
    "content": "yo",
    "ts": "2026-01-01T00:00:01+00:00",
    "uuid": "a",
}


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
        w = next_inner_tick_wait_seconds(
            store,
            last_inner_fire_monotonic=None,
            last_maintenance_transcript_line_count=None,
        )
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
        last_maintenance_transcript_line_count=None,
        overrides=InnerTickScheduleOverrides(enabled=False),
    )
    assert w >= 86400.0 * 300


def test_next_inner_tick_bootstrap_context_mode_disables(tmp_path: Path) -> None:
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
        "context.json",
        json.dumps({"context_mode": "bootstrap"}, ensure_ascii=False),
    )
    w = next_inner_tick_wait_seconds(
        store,
        last_inner_fire_monotonic=None,
        last_maintenance_transcript_line_count=None,
    )
    assert w >= 86400.0 * 300


def test_next_inner_tick_skips_when_transcript_unchanged(tmp_path: Path) -> None:
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
        last_maintenance_transcript_line_count=len(rows),
    )
    assert w >= 86400.0 * 300


def test_transcript_tail_message_uuid_returns_last_business_row(tmp_path: Path) -> None:
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


def test_maintenance_due_offline_first_fire_without_state(tmp_path: Path) -> None:
    sc = CompanionScope("it", "a", f"off-first-{tmp_path.name}")
    store = _write_transcript_store(sc, [_USER_ROW, _ASSISTANT_ROW])
    assert (
        maintenance_due_offline(
            store,
            now_utc=datetime.now(timezone.utc),
            last_fired_at_utc=None,
            last_transcript_line_count=None,
            min_gap_seconds=120.0,
            min_transcript_msgs=2,
        )
        is True
    )


def test_maintenance_due_offline_blocked_within_min_gap(tmp_path: Path) -> None:
    sc = CompanionScope("it", "a", f"off-gap-{tmp_path.name}")
    store = _write_transcript_store(sc, [_USER_ROW, _ASSISTANT_ROW])
    now = datetime.now(timezone.utc)
    assert (
        maintenance_due_offline(
            store,
            now_utc=now,
            last_fired_at_utc=now - timedelta(seconds=60),
            last_transcript_line_count=1,
            min_gap_seconds=120.0,
            min_transcript_msgs=2,
        )
        is False
    )


def test_maintenance_due_offline_ready_after_min_gap(tmp_path: Path) -> None:
    sc = CompanionScope("it", "a", f"off-ready-{tmp_path.name}")
    store = _write_transcript_store(sc, [_USER_ROW, _ASSISTANT_ROW])
    now = datetime.now(timezone.utc)
    assert (
        maintenance_due_offline(
            store,
            now_utc=now,
            last_fired_at_utc=now - timedelta(seconds=200),
            last_transcript_line_count=1,
            min_gap_seconds=120.0,
            min_transcript_msgs=2,
        )
        is True
    )


def test_maintenance_due_offline_skips_when_transcript_unchanged(
    tmp_path: Path,
) -> None:
    sc = CompanionScope("it", "a", f"off-unchanged-{tmp_path.name}")
    store = _write_transcript_store(sc, [_USER_ROW, _ASSISTANT_ROW])
    now = datetime.now(timezone.utc)
    assert (
        maintenance_due_offline(
            store,
            now_utc=now,
            last_fired_at_utc=now - timedelta(seconds=999),
            last_transcript_line_count=2,
            min_gap_seconds=120.0,
            min_transcript_msgs=2,
        )
        is False
    )


def test_maintenance_due_offline_skips_when_tail_not_assistant(
    tmp_path: Path,
) -> None:
    sc = CompanionScope("it", "a", f"off-tail-{tmp_path.name}")
    tail_user = {**_USER_ROW, "uuid": "u2", "content": "again"}
    store = _write_transcript_store(sc, [_USER_ROW, _ASSISTANT_ROW, tail_user])
    assert (
        maintenance_due_offline(
            store,
            now_utc=datetime.now(timezone.utc),
            last_fired_at_utc=None,
            last_transcript_line_count=None,
            min_gap_seconds=120.0,
            min_transcript_msgs=2,
        )
        is False
    )


def test_maintenance_due_offline_bootstrap_context_disables(
    tmp_path: Path,
) -> None:
    sc = CompanionScope("it", "a", f"off-boot-{tmp_path.name}")
    store = _write_transcript_store(sc, [_USER_ROW, _ASSISTANT_ROW])
    store.write_document(
        "context.json",
        json.dumps({"context_mode": "bootstrap"}, ensure_ascii=False),
    )
    assert (
        maintenance_due_offline(
            store,
            now_utc=datetime.now(timezone.utc),
            last_fired_at_utc=None,
            last_transcript_line_count=None,
            min_gap_seconds=120.0,
            min_transcript_msgs=2,
        )
        is False
    )
