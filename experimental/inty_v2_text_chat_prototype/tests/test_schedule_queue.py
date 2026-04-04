"""Non-LLM schedule queue kernel: persistence, due emission, ack/retry."""

from __future__ import annotations

import json
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
import sys

if str(_EXPERIMENTAL) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.paths import WorkspacePaths
from inty_v2_text_chat_prototype.schedule_queue import (
    add_schedule_task,
    mark_task_fired,
    mark_task_retry,
    next_due_wait_seconds,
    pending_task_count,
    pop_due_task_events_nowait,
    start_schedule_scheduler,
    stop_schedule_scheduler,
)
import inty_v2_text_chat_prototype.schedule_queue as schedule_queue


class TestScheduleQueueKernel(unittest.TestCase):
    def test_add_and_due_emission_and_ack(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            due = (datetime.now(timezone.utc) + timedelta(milliseconds=80)).isoformat()
            task = add_schedule_task(root, exec_time_utc=due, task_text="出门")
            self.assertEqual(pending_task_count(root), 1)
            self.assertTrue(WorkspacePaths(root=root).schedule_queue_json.is_file())
            start_schedule_scheduler(root)
            try:
                deadline = time.time() + 2.0
                evs = []
                while time.time() < deadline:
                    evs = pop_due_task_events_nowait(workspace=root)
                    if evs:
                        break
                    time.sleep(0.02)
                self.assertEqual(len(evs), 1)
                self.assertEqual(evs[0].task_id, task.id)
                self.assertEqual(evs[0].task_text, "出门")
                self.assertTrue(mark_task_fired(root, task.id))
                self.assertEqual(pending_task_count(root), 0)
            finally:
                stop_schedule_scheduler(root)

    def test_retry_requeues_task(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            due = datetime.now(timezone.utc).isoformat()
            task = add_schedule_task(root, exec_time_utc=due, task_text="喝水")
            start_schedule_scheduler(root)
            try:
                deadline = time.time() + 2.0
                got = None
                while time.time() < deadline:
                    evs = pop_due_task_events_nowait(workspace=root)
                    if evs:
                        got = evs[0]
                        break
                    time.sleep(0.02)
                self.assertIsNotNone(got)
                self.assertTrue(mark_task_retry(root, task.id, "boom"))
                self.assertEqual(pending_task_count(root), 1)
                wait = next_due_wait_seconds(root)
                self.assertIsNotNone(wait)
                assert wait is not None
                self.assertGreater(wait, 0.0)
            finally:
                stop_schedule_scheduler(root)

    def test_next_due_wait_none_when_no_pending(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.assertIsNone(next_due_wait_seconds(root))

    def test_invalid_timestamp_task_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            queue_path = WorkspacePaths(root=root).schedule_queue_json
            queue_path.write_text(
                json.dumps(
                    {
                        "tasks": [
                            {
                                "id": "bad-1",
                                "exec_time_utc": "not-a-time",
                                "task_text": "坏任务",
                                "status": "pending",
                                "created_at_utc": "2026-01-01T00:00:00+00:00",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            self.assertIsNone(next_due_wait_seconds(root))

            due = datetime.now(timezone.utc).isoformat()
            task = add_schedule_task(root, exec_time_utc=due, task_text="好任务")
            start_schedule_scheduler(root)
            try:
                deadline = time.time() + 2.0
                got = None
                while time.time() < deadline:
                    evs = pop_due_task_events_nowait(workspace=root)
                    if evs:
                        got = evs[0]
                        break
                    time.sleep(0.02)
                self.assertIsNotNone(got)
                assert got is not None
                self.assertEqual(got.task_id, task.id)
            finally:
                stop_schedule_scheduler(root)

    def test_stop_scheduler_joins_thread(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            start_schedule_scheduler(root)
            runner = schedule_queue._runner_for(root)
            self.assertIsNotNone(runner)
            assert runner is not None
            with patch.object(runner.thread, "join", wraps=runner.thread.join) as join_spy:
                stop_schedule_scheduler(root)
                self.assertTrue(join_spy.called)


if __name__ == "__main__":
    unittest.main()
