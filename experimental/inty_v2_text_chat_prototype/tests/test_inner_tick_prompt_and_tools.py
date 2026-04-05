"""内在节拍：system 契约与精简 REPL 工具集。"""

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
from inty_v2_text_chat_prototype.workspace_init_tools import (
    build_openai_repl_tools,
    build_openai_repl_tools_inner_tick,
)


class TestInnerTickPromptAndTools(unittest.TestCase):
    def test_inner_tick_tool_subset(self) -> None:
        inner = build_openai_repl_tools_inner_tick()
        full = build_openai_repl_tools()
        inner_names = {t["function"]["name"] for t in inner}
        self.assertEqual(
            inner_names,
            {
                "user_profile_record",
                "workspace_list_dir",
                "workspace_read_file",
                "workspace_write_file",
            },
        )
        self.assertEqual(len(inner), 4)
        full_names = {t["function"]["name"] for t in full}
        self.assertTrue(inner_names.issubset(full_names))
        banned = (
            "schedule_task",
            "google_web_search",
            "generate_image",
            "modify_image",
            "tool_update_chat_settings",
        )
        for b in banned:
            self.assertNotIn(b, inner_names)

    def test_build_system_prompt_inner_tick_contract(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_workspace(root, write_context=False)
            paths = WorkspacePaths(root=root)
            bundle = load_prompt_bundle(paths, meta=ContextMeta())
            system = build_system_prompt(
                bundle,
                ContextMeta(),
                enable_user_profile_tool=True,
                inner_tick_turn=True,
                ai_private_text="",
            )
            self.assertIn("## 本轮（内在节拍）", system)
            self.assertIn("模拟一次拟人的、向内的思考节拍", system)
            self.assertIn("## 内在节拍输出与工具契约", system)
            self.assertIn("本回合 API 侧**可以**携带工具列表", system)
            self.assertNotIn(
                "输出通道：仅自然语言文本回复；本回合无工具调用", system
            )


if __name__ == "__main__":
    unittest.main()
