"""每轮记忆管线：MEMORY → USER → SOUL 策展顺序与开关。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.bootstrap import init_workspace
from inty_v2_text_chat_prototype.memory_update import memory_update_after_turn
from inty_v2_text_chat_prototype.paths import WorkspacePaths


class TestSoulMemoryUpdate(unittest.TestCase):
    def test_soul_rewritten_after_memory_when_day_summary_off(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            init_workspace(root)
            paths = WorkspacePaths(root=root)
            env = {
                "INTY_V2_PROTO_DAY_SUMMARY_DISABLED": "1",
                "INTY_V2_PROTO_USER_UPDATE_EVERY_N_TURNS": "1",
            }
            with patch.dict("os.environ", env, clear=False):
                with patch(
                    "inty_v2_text_chat_prototype.memory_update.complete"
                ) as m_complete:
                    m_complete.side_effect = [
                        "# MEMORY\n\nx\n",
                        "# USER\n\nz\n",
                        "# SOUL\n\ny\n",
                    ]
                    memory_update_after_turn(
                        paths,
                        user_text="用户",
                        assistant_text="助手",
                    )
            self.assertEqual(paths.memory_md.read_text(encoding="utf-8"), "# MEMORY\n\nx\n")
            self.assertEqual(paths.user_md.read_text(encoding="utf-8"), "# USER\n\nz\n")
            self.assertEqual(paths.soul.read_text(encoding="utf-8"), "# SOUL\n\ny\n")

    def test_soul_skipped_when_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            init_workspace(root)
            paths = WorkspacePaths(root=root)
            original_soul = paths.soul.read_text(encoding="utf-8")
            env = {
                "INTY_V2_PROTO_DAY_SUMMARY_DISABLED": "1",
                "INTY_V2_PROTO_USER_UPDATE_EVERY_N_TURNS": "1",
                "INTY_V2_PROTO_SOUL_UPDATE_DISABLED": "1",
            }
            with patch.dict("os.environ", env, clear=False):
                with patch(
                    "inty_v2_text_chat_prototype.memory_update.complete"
                ) as m_complete:
                    m_complete.side_effect = ["# MEMORY\n\nx\n", "# USER\n\nz\n"]
                    memory_update_after_turn(
                        paths,
                        user_text="u",
                        assistant_text="a",
                    )
            self.assertEqual(m_complete.call_count, 2)
            self.assertEqual(paths.user_md.read_text(encoding="utf-8"), "# USER\n\nz\n")
            self.assertEqual(paths.soul.read_text(encoding="utf-8"), original_soul)

    def test_user_skipped_when_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            init_workspace(root)
            paths = WorkspacePaths(root=root)
            original_user = paths.user_md.read_text(encoding="utf-8")
            env = {
                "INTY_V2_PROTO_DAY_SUMMARY_DISABLED": "1",
                "INTY_V2_PROTO_USER_UPDATE_DISABLED": "1",
            }
            with patch.dict("os.environ", env, clear=False):
                with patch(
                    "inty_v2_text_chat_prototype.memory_update.complete"
                ) as m_complete:
                    m_complete.side_effect = ["# MEMORY\n\nx\n", "# SOUL\n\ny\n"]
                    memory_update_after_turn(
                        paths,
                        user_text="u",
                        assistant_text="a",
                    )
            self.assertEqual(m_complete.call_count, 2)
            self.assertEqual(paths.user_md.read_text(encoding="utf-8"), original_user)
            self.assertEqual(paths.soul.read_text(encoding="utf-8"), "# SOUL\n\ny\n")


if __name__ == "__main__":
    unittest.main()
