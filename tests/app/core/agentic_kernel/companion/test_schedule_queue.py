from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.agentic_kernel.companion.memory_registry import get_memory_store
from app.core.agentic_kernel.companion.schedule_queue import (
    _schedule_document_rel_path,
    add_schedule_task,
    get_due_tasks,
    mark_task_fired,
)


def test_add_and_get_due_tasks(tmp_path: Path) -> None:
    root = tmp_path
    root.mkdir(exist_ok=True)
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    tid = add_schedule_task(root, exec_time_utc=past, task_text="remind me")
    due = get_due_tasks(root)
    assert len(due) == 1
    assert due[0]["id"] == tid
    assert due[0]["task_text"] == "remind me"


def test_mark_task_fired(tmp_path: Path) -> None:
    root = tmp_path
    root.mkdir(exist_ok=True)
    past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    tid = add_schedule_task(root, exec_time_utc=past, task_text="x")
    assert len(get_due_tasks(root)) == 1
    mark_task_fired(root, tid)
    assert get_due_tasks(root) == []


def test_legacy_top_level_array_rewritten_as_tasks_object(tmp_path: Path) -> None:
    root = tmp_path
    root.mkdir(exist_ok=True)
    store = get_memory_store(root)
    rel = _schedule_document_rel_path(root)
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
    add_schedule_task(root, exec_time_utc=future, task_text="new")
    body = json.loads(store.read_document(rel))
    assert isinstance(body.get("tasks"), list)
    ids = {t["id"] for t in body["tasks"]}
    assert legacy_id in ids
    assert len(ids) == 2
