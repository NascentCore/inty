"""BOOSTRAP.md：收尾须包含邀请共同定义与询问对方基本信息（可执行规范）。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.workspace_init_loop import (
    load_bootstrap_instruction_text,
)


class TestBootstrapSpecOnboarding(unittest.TestCase):
    def test_closure_invites_co_definition_and_user_info(self) -> None:
        text = load_bootstrap_instruction_text()
        self.assertIn("收尾", text)
        self.assertIn("定义你", text)
        self.assertIn("基本信息", text)

    def test_supports_companion_type_specific_templates(self) -> None:
        self.assertIn("伴侣", load_bootstrap_instruction_text("伴侣"))
        self.assertIn("朋友", load_bootstrap_instruction_text("朋友"))
        self.assertIn("爱人", load_bootstrap_instruction_text("爱人"))
        self.assertIn("亲人", load_bootstrap_instruction_text("亲人"))

    def test_supports_custom_companion_type(self) -> None:
        text = load_bootstrap_instruction_text("同事")
        self.assertIn("当前陪伴类型: 同事", text)
        self.assertIn("自定义关系类型陪伴", text)


if __name__ == "__main__":
    unittest.main()
