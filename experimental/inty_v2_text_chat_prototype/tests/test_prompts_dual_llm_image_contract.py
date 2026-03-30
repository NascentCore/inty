"""Dual-LLM: image tool contract only on tool branch (build_system_prompt flag)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.bootstrap import init_workspace
from inty_v2_text_chat_prototype.models import (
    ContextMeta,
    PromptBundle,
    load_prompt_bundle,
)
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
        self.assertIn("google_web_search", full_sys)
        self.assertNotIn("google_web_search", chat_sys)
        self.assertNotIn("generate_image", chat_sys)
        self.assertNotIn("modify_image", chat_sys)
        self.assertNotIn("（4）", chat_sys)
        self.assertNotIn("user_profile_record", chat_sys)
        self.assertNotIn("workspace_read_file", chat_sys)
        self.assertIn("无工具调用", chat_sys)

    def test_tool_side_compact_omits_memory_and_inserts_directive(self) -> None:
        bundle = PromptBundle(
            identity="脸：测试",
            soul="很长的扮演设定" * 20,
            user_md="用户档案",
            memory_md="长期记忆唯一标记 XYZ_MEMORY_MARK",
            memory_raw_diary_today_md="日记唯一标记 ABC_DIARY",
            memory_day_summary_today_md="当日总结 DEF_SUMMARY",
        )
        full_sys = build_system_prompt(
            bundle,
            ContextMeta(),
            enable_user_profile_tool=True,
            include_repl_image_generation_contract=True,
            tool_side_compact=False,
        )
        compact_sys = build_system_prompt(
            bundle,
            ContextMeta(),
            enable_user_profile_tool=True,
            include_repl_image_generation_contract=True,
            tool_side_compact=True,
        )
        self.assertIn("XYZ_MEMORY_MARK", full_sys)
        self.assertIn("ABC_DIARY", full_sys)
        self.assertNotIn("XYZ_MEMORY_MARK", compact_sys)
        self.assertNotIn("ABC_DIARY", compact_sys)
        self.assertNotIn("DEF_SUMMARY", compact_sys)
        self.assertIn("工具侧（后台）", compact_sys)
        self.assertIn("联网检索", compact_sys)
        self.assertIn("generate_image", compact_sys)


if __name__ == "__main__":
    unittest.main()
