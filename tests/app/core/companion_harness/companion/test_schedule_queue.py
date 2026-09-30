from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.core.companion_harness.companion.schedule_queue import (
    _schedule_document_rel,
    add_schedule_task,
    mark_task_fired,
    next_due_task_for_execution,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)


def _store(tmp: Path):
    return MemoryStore(
        scope=CompanionScope("sq", "a", tmp.name),
        repository=None,
    )


def test_schedule_document_rel_matches_scope_path_accessor() -> None:
    assert (
        _schedule_document_rel()
        == DEFAULT_MEMORY_STORE_SCOPE_PATHS.schedule_queue_json
    )


def test_add_and_next_due_task(tmp_path: Path) -> None:
    store = _store(tmp_path)
    past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    tid = add_schedule_task(store, exec_time_utc=past, task_text="remind me")
    due = next_due_task_for_execution(store)
    assert due is not None
    assert due.id == tid
    assert due.task_text == "remind me"


def test_next_due_task_for_execution_picks_earliest_ready(
    tmp_path: Path,
) -> None:
    store = _store(Path(str(tmp_path) + "-ndue"))
    t_later = add_schedule_task(
        store,
        exec_time_utc="2020-01-01T01:00:00+00:00",
        task_text="later",
    )
    t_earlier = add_schedule_task(
        store,
        exec_time_utc="2020-01-01T00:00:00+00:00",
        task_text="earlier",
    )

    first = next_due_task_for_execution(store)
    assert first is not None
    assert first.id == t_earlier
    mark_task_fired(store, t_earlier)
    second = next_due_task_for_execution(store)
    assert second is not None
    assert second.id == t_later


def test_schedule_queue_rejects_legacy_array_document(tmp_path: Path) -> None:
    store = _store(Path(str(tmp_path) + "-legacy"))
    rel = _schedule_document_rel()
    past = "2025-01-01T00:00:00+00:00"
    store.write_document(
        rel,
        json.dumps(
            [
                {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "exec_time_utc": past,
                    "task_text": "legacy",
                    "status": "pending",
                    "created_at_utc": past,
                }
            ],
            ensure_ascii=False,
        )
        + "\n",
    )
    future = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    with pytest.raises(
        ValueError,
        match="schedule tasks document must be a JSON object",
    ):
        add_schedule_task(store, exec_time_utc=future, task_text="new")


def test_add_schedule_task_accepts_z_and_rejects_naive_time(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)

    add_schedule_task(
        store,
        exec_time_utc="2026-01-01T00:00:00Z",
        task_text="midnight",
    )
    body = json.loads(store.read_document(_schedule_document_rel()))
    assert body["tasks"][0]["exec_time_utc"] == "2026-01-01T00:00:00+00:00"

    with pytest.raises(ValueError, match="timezone offset or Z"):
        add_schedule_task(
            store,
            exec_time_utc="2026-01-01T00:00:00",
            task_text="naive",
        )
