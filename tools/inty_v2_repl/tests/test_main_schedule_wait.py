"""REPL idle wait now includes schedule due events."""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from experimental.inty_v2_text_chat_prototype.main import _next_idle_wait_seconds
from experimental.inty_v2_text_chat_prototype.schedule_queue import add_schedule_task


class TestMainScheduleWait(unittest.TestCase):
    def test_without_inner_tick_uses_due_task_wait(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            t = (datetime.now(timezone.utc) + timedelta(seconds=2)).isoformat()
            add_schedule_task(root, exec_time_utc=t, task_text="提醒喝水")
            wait = _next_idle_wait_seconds(
                ws=root, inner_tick=False, last_inner_fire_mono=None
            )
            self.assertLess(wait, 3.0)
            self.assertGreater(wait, 0.0)


if __name__ == "__main__":
    unittest.main()
