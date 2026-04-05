"""BOOSTRAP.md：可加载；bootstrap system 拼接 canonical 四份人格模板形状。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.bootstrap import init_workspace
from inty_v2_text_chat_prototype.memory_store_registry import shutdown_memory_store
from inty_v2_text_chat_prototype.workspace_init_loop import (
    build_bootstrap_system_prompt,
    load_bootstrap_instruction_text,
)


class TestBootstrapSpecOnboarding(unittest.TestCase):
    def test_closure_invites_co_definition_and_user_info(self) -> None:
        text = load_bootstrap_instruction_text()
        self.assertIn("收尾", text)
        self.assertIn("定义你", text)
        self.assertIn("关键信息", text)

    def test_spec_requires_ai_to_confirm_companionship_type(self) -> None:
        text = load_bootstrap_instruction_text()
        self.assertIn("陪伴模式", text)
        self.assertIn("关系建立", text)
        self.assertIn("工具**更新**", text)

    def test_init_workspace_copies_boostrap_load_uses_workspace_copy(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            init_workspace(root, write_context=False)
            boostrap = root / "BOOSTRAP.md"
            self.assertTrue(boostrap.is_file())
            text = load_bootstrap_instruction_text(root)
            self.assertIn("收尾", text)
            shutdown_memory_store(root, timeout_s=2.0)

    def test_bootstrap_system_embeds_package_template_shapes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            root.mkdir()
            (root / "BOOSTRAP.md").write_text("# stub spec\n", encoding="utf-8")
            s = build_bootstrap_system_prompt(root)
            self.assertIn("canonical_workspace_md_shapes", s)
            self.assertIn("### IDENTITY.md", s)
            self.assertIn("# 身份定义", s)
            self.assertIn("### SOUL.md", s)
            self.assertIn("# 内在灵魂", s)
            self.assertIn("### USER.md", s)
            self.assertIn("# 用户画像", s)
            self.assertIn("### MEMORY.md", s)
            self.assertIn("# 共同记忆", s)


if __name__ == "__main__":
    unittest.main()
