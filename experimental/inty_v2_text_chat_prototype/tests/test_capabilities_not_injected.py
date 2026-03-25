"""CAPABILITIES.md 存在时也不进入 system prompt（不注入）。"""

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


class TestCapabilitiesNotInjected(unittest.TestCase):
    def test_capabilities_file_ignored_in_system_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_workspace(root, write_context=False)
            marker = "CAPABILITIES_SHOULD_NEVER_APPEAR_IN_SYSTEM_xyz"
            (root / "CAPABILITIES.md").write_text(f"# x\n{marker}\n", encoding="utf-8")
            paths = WorkspacePaths(root=root)
            bundle = load_prompt_bundle(paths, meta=ContextMeta())
            system = build_system_prompt(
                bundle, ContextMeta(), enable_user_profile_tool=True
            )
            self.assertNotIn(marker, system)
            self.assertNotIn("## CAPABILITIES（基础能力与限制）", system)


if __name__ == "__main__":
    unittest.main()
