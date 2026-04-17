"""USER.md 策展 LLM 按 INTY_V2_PROTO_USER_UPDATE_EVERY_N_TURNS 间隔运行。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_repl.bootstrap import init_workspace
from inty_v2_repl.memory_update import memory_update_after_turn
from inty_v2_repl.paths import WorkspacePaths


class TestUserUpdateInterval(unittest.TestCase):
    def test_every_n_turns_skips_until_nth(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            init_workspace(root)
            paths = WorkspacePaths(root=root)
            env = {
                "INTY_V2_PROTO_DAY_SUMMARY_DISABLED": "1",
                "INTY_V2_PROTO_USER_UPDATE_EVERY_N_TURNS": "3",
                "INTY_V2_PROTO_MEMORY_UPDATE_EVERY_N_TURNS": "1",
                "INTY_V2_PROTO_SOUL_UPDATE_EVERY_N_TURNS": "1",
            }
            with patch.dict("os.environ", env, clear=False):
                with patch(
                    "inty_v2_repl.memory_update.complete"
                ) as m_complete:
                    m_complete.side_effect = [
                        "# MEMORY\n\na1\n",
                        "# SOUL\n\ns1\n",
                    ]
                    memory_update_after_turn(
                        paths,
                        user_text="u",
                        assistant_text="a 底线",
                    )
                    self.assertEqual(m_complete.call_count, 2)

                    m_complete.side_effect = [
                        "# MEMORY\n\na2\n",
                        "# SOUL\n\ns2\n",
                    ]
                    memory_update_after_turn(
                        paths,
                        user_text="u",
                        assistant_text="a 底线",
                    )
                    self.assertEqual(m_complete.call_count, 4)

                    m_complete.side_effect = [
                        "# MEMORY\n\na3\n",
                        "# USER\n\nu3\n",
                        "# SOUL\n\ns3\n",
                    ]
                    memory_update_after_turn(
                        paths,
                        user_text="u",
                        assistant_text="a 底线",
                    )
                    self.assertEqual(m_complete.call_count, 7)

            self.assertEqual(
                paths.user_md.read_text(encoding="utf-8"), "# USER\n\nu3\n"
            )


if __name__ == "__main__":
    unittest.main()
