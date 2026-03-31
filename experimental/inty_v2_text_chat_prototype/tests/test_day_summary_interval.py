"""当日总结 LLM 按 INTY_V2_PROTO_DAY_SUMMARY_EVERY_N_TURNS 间隔运行。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.bootstrap import init_workspace
from inty_v2_text_chat_prototype.memory_store_registry import shutdown_memory_store
from inty_v2_text_chat_prototype.memory_update import memory_update_after_turn
from inty_v2_text_chat_prototype.paths import WorkspacePaths
from inty_v2_text_chat_prototype.utc import local_date_str


class TestDaySummaryInterval(unittest.TestCase):
    def test_every_n_turns_skips_until_nth(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            init_workspace(root)
            paths = WorkspacePaths(root=root)
            env = {
                "INTY_V2_PROTO_DAY_SUMMARY_EVERY_N_TURNS": "3",
                "INTY_V2_PROTO_MEMORY_UPDATE_EVERY_N_TURNS": "1",
                "INTY_V2_PROTO_USER_UPDATE_EVERY_N_TURNS": "1",
                "INTY_V2_PROTO_SOUL_UPDATE_EVERY_N_TURNS": "1",
                "INTY_V2_PROTO_SOUL_UPDATE_REQUIRE_FUNDAMENTAL_SIGNAL": "0",
            }
            with patch.dict("os.environ", env, clear=False):
                with patch(
                    "inty_v2_text_chat_prototype.memory_update.complete"
                ) as m_complete:
                    # turn 1: memory, user, soul — no day_summary
                    m_complete.side_effect = [
                        "# MEMORY\n\na1\n",
                        "# USER\n\nu1\n",
                        "# SOUL\n\ns1\n",
                    ]
                    memory_update_after_turn(
                        paths,
                        user_text="u",
                        assistant_text="a",
                    )
                    self.assertEqual(m_complete.call_count, 3)

                    m_complete.side_effect = [
                        "# MEMORY\n\na2\n",
                        "# USER\n\nu2\n",
                        "# SOUL\n\ns2\n",
                    ]
                    memory_update_after_turn(
                        paths,
                        user_text="u",
                        assistant_text="a",
                    )
                    self.assertEqual(m_complete.call_count, 6)

                    m_complete.side_effect = [
                        "# day\n",
                        "# MEMORY\n\na3\n",
                        "# USER\n\nu3\n",
                        "# SOUL\n\ns3\n",
                    ]
                    memory_update_after_turn(
                        paths,
                        user_text="u",
                        assistant_text="a",
                    )
                    self.assertEqual(m_complete.call_count, 10)

            day = paths.memory_day_summary(local_date_str())
            self.assertTrue(day.is_file())
            self.assertIn("# day", day.read_text(encoding="utf-8"))
            shutdown_memory_store(root, timeout_s=2.0)


if __name__ == "__main__":
    unittest.main()
