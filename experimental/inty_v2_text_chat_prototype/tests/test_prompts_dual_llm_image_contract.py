"""Dual-LLM: image tool contract only on tool branch (build_system_prompt flag)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.bootstrap import init_workspace
from inty_v2_text_chat_prototype.models import ContextMeta, load_prompt_bundle
from inty_v2_text_chat_prototype.paths import WorkspacePaths
from inty_v2_text_chat_prototype.prompts import build_system_prompt


class TestDualLlmImageContract(unittest.TestCase):
    def test_chat_branch_omits_generate_image_clause(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_workspace(root, write_context=False)
            paths = WorkspacePaths(root=root)
            bundle = load_prompt_bundle(paths, meta=ContextMeta())
            full_sys = build_system_prompt(
                bundle,
                ContextMeta(),
                enable_user_profile_tool=True,
                include_repl_image_generation_contract=True,
            )
            chat_sys = build_system_prompt(
                bundle,
                ContextMeta(),
                enable_user_profile_tool=True,
                include_repl_image_generation_contract=False,
            )
        self.assertIn("generate_image", full_sys)
        self.assertIn("modify_image", full_sys)
        self.assertNotIn("generate_image", chat_sys)
        self.assertNotIn("modify_image", chat_sys)
        self.assertIn("（4）", chat_sys)
        self.assertIn("user_profile_record", chat_sys)


if __name__ == "__main__":
    unittest.main()
