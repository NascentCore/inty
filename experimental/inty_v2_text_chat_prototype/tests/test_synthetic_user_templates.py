"""Package `templates/SYNTH_USER_*.md`：合成 user 文案可被加载。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.bootstrap import read_package_template_text


class TestSyntheticUserTemplates(unittest.TestCase):
    def test_bootstrap_agent_default_contains_companionship(self) -> None:
        s = read_package_template_text("SYNTH_USER_BOOTSTRAP_AGENT_DEFAULT.md")
        self.assertIn("companionship", s)
        self.assertIn("终端", s)

    def test_repl_template_bootstrap_opening_mentions_boostraped(self) -> None:
        s = read_package_template_text("SYNTH_USER_REPL_TEMPLATE_BOOTSTRAP_OPENING.md")
        self.assertIn("BOOSTRAPED", s)
        self.assertIn("IDENTITY", s)

    def test_repl_startup_profile_inquiry_is_short_turn_rule(self) -> None:
        s = read_package_template_text("SYNTH_USER_REPL_STARTUP_PROFILE_INQUIRY.md")
        self.assertIn("companionship", s)
        self.assertIn("工作区", s)


if __name__ == "__main__":
    unittest.main()
