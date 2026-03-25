"""CAPABILITIES.md：load_prompt_bundle 与 build_system_prompt 注入顺序。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.models import ContextMeta, load_prompt_bundle
from inty_v2_text_chat_prototype.paths import WorkspacePaths
from inty_v2_text_chat_prototype.prompts import build_system_prompt


class TestCapabilitiesPrompt(unittest.TestCase):
    def test_capabilities_before_identity_before_memory_when_intimate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "IDENTITY.md").write_text("i\n", encoding="utf-8")
            (root / "SOUL.md").write_text("s\n", encoding="utf-8")
            (root / "USER.md").write_text("u\n", encoding="utf-8")
            (root / "MEMORY.md").write_text("long mem\n", encoding="utf-8")
            (root / "transcript.jsonl").write_text("", encoding="utf-8")
            (root / "CAPABILITIES.md").write_text("CAP_MARK_UNIQUE\n", encoding="utf-8")
            meta = ContextMeta(context_mode="intimate")
            paths = WorkspacePaths(root=root)
            bundle = load_prompt_bundle(paths, meta=meta)
            system = build_system_prompt(bundle, meta, enable_user_profile_tool=False)
            self.assertIn("CAP_MARK_UNIQUE", system)
            pos_c = system.find("## CAPABILITIES（基础能力与限制）")
            pos_i = system.find("## IDENTITY")
            pos_m = system.find("## MEMORY（长期记忆定稿）")
            self.assertGreater(pos_c, -1)
            self.assertGreater(pos_i, -1)
            self.assertGreater(pos_m, -1)
            self.assertLess(pos_c, pos_i)
            self.assertLess(pos_i, pos_m)

    def test_capabilities_before_identity_before_user_before_output_contract(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "IDENTITY.md").write_text("i\n", encoding="utf-8")
            (root / "SOUL.md").write_text("s\n", encoding="utf-8")
            (root / "USER.md").write_text("u\n", encoding="utf-8")
            (root / "MEMORY.md").write_text("", encoding="utf-8")
            (root / "CAPABILITIES.md").write_text("cap body\n", encoding="utf-8")
            meta = ContextMeta(context_mode="public")
            paths = WorkspacePaths(root=root)
            bundle = load_prompt_bundle(paths, meta=meta)
            system = build_system_prompt(bundle, meta, enable_user_profile_tool=True)
            pos_c = system.find("## CAPABILITIES（基础能力与限制）")
            pos_i = system.find("## IDENTITY")
            pos_u = system.find("## USER")
            pos_out = system.find("输出与工具")
            self.assertLess(pos_c, pos_i)
            self.assertLess(pos_i, pos_u)
            self.assertLess(pos_u, pos_out)

    def test_omitted_when_capabilities_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "IDENTITY.md").write_text("i\n", encoding="utf-8")
            (root / "SOUL.md").write_text("s\n", encoding="utf-8")
            (root / "USER.md").write_text("u\n", encoding="utf-8")
            (root / "MEMORY.md").write_text("m\n", encoding="utf-8")
            meta = ContextMeta(context_mode="intimate")
            paths = WorkspacePaths(root=root)
            bundle = load_prompt_bundle(paths, meta=meta)
            system = build_system_prompt(bundle, meta)
            self.assertNotIn("## CAPABILITIES（基础能力与限制）", system)


if __name__ == "__main__":
    unittest.main()
