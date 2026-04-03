"""Non-LLM schedule queue kernel: persistence, due emission, ack/retry."""

from __future__ import annotations

import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
