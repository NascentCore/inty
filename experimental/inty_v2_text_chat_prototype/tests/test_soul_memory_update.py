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
from inty_v2_text_chat_prototype.memory_store_registry import shutdown_memory_store
from inty_v2_text_chat_prototype.paths import WorkspacePaths

# SOUL 策展默认需「底线/边界/…」等信号；测试里在助手侧带一词以触发。
_TURN_SOUL = ("用户", "助手 底线")


class TestSoulMemoryUpdate(unittest.TestCase):
    def test_soul_rewritten_after_memory_when_day_summary_off(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            init_workspace(root)
            paths = WorkspacePaths(root=root)
            user_path = root / "USER.md"
            soul_path = root / "SOUL.md"
            memory_path = root / "MEMORY.md"
            env = {
                "INTY_V2_PROTO_DAY_SUMMARY_DISABLED": "1",
                "INTY_V2_PROTO_MEMORY_UPDATE_EVERY_N_TURNS": "1",
                "INTY_V2_PROTO_USER_UPDATE_EVERY_N_TURNS": "1",
                "INTY_V2_PROTO_SOUL_UPDATE_EVERY_N_TURNS": "1",
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
                        user_text=_TURN_SOUL[0],
                        assistant_text=_TURN_SOUL[1],
                    )
            self.assertEqual(memory_path.read_text(encoding="utf-8"), "# MEMORY\n\nx\n")
            self.assertEqual(user_path.read_text(encoding="utf-8"), "# USER\n\nz\n")
            self.assertEqual(soul_path.read_text(encoding="utf-8"), "# SOUL\n\ny\n")
            shutdown_memory_store(root, timeout_s=2.0)

    def test_soul_skipped_when_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            init_workspace(root)
            paths = WorkspacePaths(root=root)
            soul_path = root / "SOUL.md"
            user_path = root / "USER.md"
            original_soul = soul_path.read_text(encoding="utf-8")
            env = {
                "INTY_V2_PROTO_DAY_SUMMARY_DISABLED": "1",
                "INTY_V2_PROTO_MEMORY_UPDATE_EVERY_N_TURNS": "1",
                "INTY_V2_PROTO_USER_UPDATE_EVERY_N_TURNS": "1",
                "INTY_V2_PROTO_SOUL_UPDATE_EVERY_N_TURNS": "1",
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
                        assistant_text="a 底线",
                    )
            self.assertEqual(m_complete.call_count, 2)
            self.assertEqual(user_path.read_text(encoding="utf-8"), "# USER\n\nz\n")
            self.assertEqual(soul_path.read_text(encoding="utf-8"), original_soul)
            shutdown_memory_store(root, timeout_s=2.0)

    def test_user_skipped_when_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            init_workspace(root)
            paths = WorkspacePaths(root=root)
            user_path = root / "USER.md"
            soul_path = root / "SOUL.md"
            original_user = user_path.read_text(encoding="utf-8")
            env = {
                "INTY_V2_PROTO_DAY_SUMMARY_DISABLED": "1",
                "INTY_V2_PROTO_MEMORY_UPDATE_EVERY_N_TURNS": "1",
                "INTY_V2_PROTO_USER_UPDATE_DISABLED": "1",
                "INTY_V2_PROTO_SOUL_UPDATE_EVERY_N_TURNS": "1",
            }
            with patch.dict("os.environ", env, clear=False):
                with patch(
                    "inty_v2_text_chat_prototype.memory_update.complete"
                ) as m_complete:
                    m_complete.side_effect = ["# MEMORY\n\nx\n", "# SOUL\n\ny\n"]
                    memory_update_after_turn(
                        paths,
                        user_text="u",
                        assistant_text="a 底线",
                    )
            self.assertEqual(m_complete.call_count, 2)
            self.assertEqual(user_path.read_text(encoding="utf-8"), original_user)
            self.assertEqual(soul_path.read_text(encoding="utf-8"), "# SOUL\n\ny\n")
            shutdown_memory_store(root, timeout_s=2.0)

    def test_soul_skipped_without_fundamental_signal(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            init_workspace(root)
            paths = WorkspacePaths(root=root)
            soul_path = root / "SOUL.md"
            original_soul = soul_path.read_text(encoding="utf-8")
            env = {
                "INTY_V2_PROTO_DAY_SUMMARY_DISABLED": "1",
                "INTY_V2_PROTO_MEMORY_UPDATE_EVERY_N_TURNS": "1",
                "INTY_V2_PROTO_USER_UPDATE_EVERY_N_TURNS": "1",
                "INTY_V2_PROTO_SOUL_UPDATE_EVERY_N_TURNS": "1",
            }
            with patch.dict("os.environ", env, clear=False):
                with patch(
                    "inty_v2_text_chat_prototype.memory_update.complete"
                ) as m_complete:
                    m_complete.side_effect = ["# MEMORY\n\nx\n", "# USER\n\nz\n"]
                    memory_update_after_turn(
                        paths,
                        user_text="你好",
                        assistant_text="嗯嗯",
                    )
            self.assertEqual(m_complete.call_count, 2)
            self.assertEqual(soul_path.read_text(encoding="utf-8"), original_soul)
            shutdown_memory_store(root, timeout_s=2.0)

    def test_soul_frozen_appearance_section_restored(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            init_workspace(root)
            paths = WorkspacePaths(root=root)
            soul_path = root / "SOUL.md"
            soul_path.write_text(
                "# SOUL\n\n## 形象（测试）\n\nHAIR\n\n## 核心\n\nold\n",
                encoding="utf-8",
            )
            env = {
                "INTY_V2_PROTO_DAY_SUMMARY_DISABLED": "1",
                "INTY_V2_PROTO_MEMORY_UPDATE_EVERY_N_TURNS": "1",
                "INTY_V2_PROTO_USER_UPDATE_EVERY_N_TURNS": "1",
                "INTY_V2_PROTO_SOUL_UPDATE_EVERY_N_TURNS": "1",
            }
            with patch.dict("os.environ", env, clear=False):
                with patch(
                    "inty_v2_text_chat_prototype.memory_update.complete"
                ) as m_complete:
                    n_calls = 0

                    def _complete_side_effect(
                        messages: list[dict[str, object]], **kwargs: object
                    ) -> str:
                        nonlocal n_calls
                        n_calls += 1
                        if n_calls == 1:
                            return "# MEMORY\n\nx\n"
                        if n_calls == 2:
                            return "# USER\n\nz\n"
                        if n_calls == 3:
                            u = str(messages[1]["content"])
                            assert "<<<SOUL_CURATOR_FROZEN_APPEARANCE>>>" in u
                            assert "HAIR" not in u
                            return (
                                "# SOUL\n\n<<<SOUL_CURATOR_FROZEN_APPEARANCE>>>\n"
                                "## 核心\n\nnew\n"
                            )
                        raise AssertionError(f"unexpected complete call {n_calls}")

                    m_complete.side_effect = _complete_side_effect
                    memory_update_after_turn(
                        paths,
                        user_text="u",
                        assistant_text="底线",
                    )
            soul_after = soul_path.read_text(encoding="utf-8")
            self.assertIn("HAIR", soul_after)
            self.assertIn("new", soul_after)
            self.assertNotIn("<<<SOUL_CURATOR_FROZEN_APPEARANCE>>>", soul_after)
            shutdown_memory_store(root, timeout_s=2.0)


if __name__ == "__main__":
    unittest.main()
