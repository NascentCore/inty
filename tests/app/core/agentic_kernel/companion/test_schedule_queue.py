from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.agentic_kernel.companion.schedule_queue import (
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
