"""templates/BOOTSTRAP.md：收尾须包含邀请共同定义与询问对方基本信息（可执行规范）。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

import inty_v2_repl.workspace_init_loop as workspace_init_loop
from inty_v2_repl.workspace_init_loop import (
    load_bootstrap_instruction_text,
)


class TestBootstrapSpecOnboarding(unittest.TestCase):
    def test_templates_boostrap_md_committed_beside_package(self) -> None:
        spec = (
            Path(workspace_init_loop.__file__).resolve().parent
            / "templates"
            / "BOOTSTRAP.md"
        )
        self.assertTrue(
            spec.is_file(),
            f"missing bootstrap spec (must be committed with workspace_init_loop): {spec}",
        )

    def test_closure_invites_co_definition_and_user_info(self) -> None:
        text = load_bootstrap_instruction_text()
        self.assertIn("收尾", text)
        self.assertIn("定义你", text)
        self.assertIn("基本信息", text)

    def test_spec_requires_ai_to_confirm_companionship_type(self) -> None:
        text = load_bootstrap_instruction_text()
        self.assertIn("companionship", text)
        self.assertIn("自然询问", text)
        self.assertIn("允许用户自定义", text)


if __name__ == "__main__":
    unittest.main()
