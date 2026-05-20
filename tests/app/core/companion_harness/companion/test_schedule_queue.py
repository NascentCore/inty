from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.schedule_queue import (
    _schedule_document_rel,
    add_schedule_task,
    get_due_tasks,
    mark_task_fired,
    next_due_task_for_execution,
)


def _store(tmp: Path):
    return MemoryStore(
        scope=CompanionScope("sq", "a", tmp.name),
        repository=None,
    )


def test_add_and_get_due_tasks(tmp_path: Path) -> None:
    store = _store(tmp_path)
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    tid = add_schedule_task(store, exec_time_utc=past, task_text="remind me")
    due = get_due_tasks(store)
    assert len(due) == 1
    assert due[0]["id"] == tid
    assert due[0]["task_text"] == "remind me"


def test_next_due_task_for_execution_picks_earliest_ready(tmp_path: Path) -> None:
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
    store = _store(Path(str(tmp_path) + "-legacy"))
    rel = _schedule_document_rel()
    legacy_id = "11111111-1111-1111-1111-111111111111"
    past = "2025-01-01T00:00:00+00:00"
    store.write_document(
        rel,
        json.dumps(
            [
                {
                    "id": legacy_id,
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
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    add_schedule_task(store, exec_time_utc=future, task_text="new")
    body = json.loads(store.read_document(rel))
    assert isinstance(body.get("tasks"), list)
    ids = {t["id"] for t in body["tasks"]}
    assert legacy_id in ids
    assert len(ids) == 2
