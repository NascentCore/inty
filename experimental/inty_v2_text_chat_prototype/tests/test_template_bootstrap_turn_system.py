"""template_bootstrap_turn_system_prompt：尚无 BOOSTRAPED 时 run_turn 所用 system 装配。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.bootstrap import init_workspace
from inty_v2_text_chat_prototype.memory_store_registry import shutdown_memory_store
from inty_v2_text_chat_prototype.orchestrator import (
    repl_template_bootstrap_opening_system_section,
    template_bootstrap_turn_system_prompt,
    template_bootstrap_turn_system_prompt_with_repl_opening,
)
from inty_v2_text_chat_prototype.prompts import system_prompt_security_prefix


class TestTemplateBootstrapTurnSystem(unittest.TestCase):
    def test_includes_security_prefix_and_canonical_shapes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            init_workspace(root, write_context=False)
            s = template_bootstrap_turn_system_prompt(root)
            self.assertIn(system_prompt_security_prefix(), s)
            self.assertIn("canonical_workspace_md_shapes", s)
            self.assertIn("# 身份定义", s)
            self.assertIn("BOOSTRAPED", s)
            self.assertIn("generate_image", s)
            self.assertIn("至多包含 1 个", s)
            shutdown_memory_store(root, timeout_s=2.0)

    def test_repl_opening_block_is_standalone_and_composes(self) -> None:
        opening = repl_template_bootstrap_opening_system_section()
        self.assertIn("用户刚打开对话", opening)
        self.assertIn("BOOSTRAPED", opening)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            init_workspace(root, write_context=False)
            full = template_bootstrap_turn_system_prompt_with_repl_opening(root)
            self.assertIn(opening, full)
            self.assertGreater(len(full), len(template_bootstrap_turn_system_prompt(root)))
            shutdown_memory_store(root, timeout_s=2.0)


if __name__ == "__main__":
    unittest.main()
