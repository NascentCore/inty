from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

from datetime import timedelta

from app.core.companion_harness.memory.memory_registry import get_memory_store
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.inner_tick_schedule import (
    InnerTickScheduleOverrides,
    inner_tick_enabled_from_env,
    next_inner_tick_wait_seconds,
)
from app.core.companion_harness.companion.sleep_state import (
    clear_inner_tick_quiet_if_circadian_day,
    inner_tick_quiet_remain_seconds,
    load_sleep_state,
    record_inner_tick_quiet_hours_from_now,
)


def _write_transcript_store(scope: CompanionScope, rows: list[dict[str, object]]) -> None:
    body = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n"
    get_memory_store(scope, dsn="").write_document("transcript.jsonl", body)


def test_inner_tick_env_unset_defaults_enabled() -> None:
    with patch.dict(os.environ, {}, clear=True):
        assert inner_tick_enabled_from_env() is True


def test_next_inner_tick_short_transcript_returns_poll_chunk(tmp_path: Path) -> None:
    sc = CompanionScope("it", "a", f"short-{tmp_path.name}")
    _write_transcript_store(
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
    store = get_memory_store(sc, dsn="")
    with patch.dict(os.environ, {}, clear=True):
        w = next_inner_tick_wait_seconds(store, last_inner_fire_monotonic=None)
    assert 0.0 < w < 86400.0 * 10


def test_next_inner_tick_overrides_enabled_false_disables(tmp_path: Path) -> None:
    sc = CompanionScope("it", "a", f"ov-{tmp_path.name}")
    _write_transcript_store(
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
    store = get_memory_store(sc, dsn="")
    w = next_inner_tick_wait_seconds(
        store,
        last_inner_fire_monotonic=None,
        overrides=InnerTickScheduleOverrides(enabled=False),
    )
    assert w >= 86400.0 * 300


def test_inner_tick_quiet_remain_and_day_clear(tmp_path: Path) -> None:
    sc = CompanionScope("it", "a", f"sleep-{tmp_path.name}")
    store = get_memory_store(sc, dsn="")
    record_inner_tick_quiet_hours_from_now(store, hours=4.0)
    st = load_sleep_state(store)
    mid = st.inner_tick_quiet_until_utc
    assert mid is not None
    before_end = mid - timedelta(hours=1)
    r = inner_tick_quiet_remain_seconds(store, now_utc=before_end)
    assert 3500.0 < r < 3700.0
    clear_inner_tick_quiet_if_circadian_day(store, is_night=False)
    st2 = load_sleep_state(store)
    assert st2.inner_tick_quiet_until_utc is None


def test_maintenance_wait_matches_max_of_schedule_and_quiet(tmp_path: Path) -> None:
    sc = CompanionScope("it", "a", f"max-{tmp_path.name}")
    _write_transcript_store(
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
    store = get_memory_store(sc, dsn="")
    record_inner_tick_quiet_hours_from_now(store, hours=10.0)
    with patch.dict(os.environ, {}, clear=True):
        sched = next_inner_tick_wait_seconds(
            store,
            last_inner_fire_monotonic=1000.0,
            now_monotonic=1000.0,
            overrides=InnerTickScheduleOverrides(
                enabled=True,
                min_gap_seconds=60.0,
                poll_seconds=60.0,
            ),
        )
    quiet = inner_tick_quiet_remain_seconds(store)
    combined = max(sched, quiet)
    assert combined == quiet
    assert combined > 60.0
