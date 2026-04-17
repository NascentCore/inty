"""user_profile_record：USER.md 合并。"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_repl.workspace_init_tools import (
    append_user_profile_facts_to_user_md,
    execute_tool_call_blocking,
    read_chat_output_format_prompt,
    tool_user_profile_record,
    tool_update_chat_settings,
)
from inty_v2_repl.memory_store_registry import shutdown_memory_store


class TestAppendUserProfileFacts(unittest.TestCase):
    def test_creates_section(self) -> None:
        base = "# 关于你\n\n## 称呼\n- x\n"
        out = append_user_profile_facts_to_user_md(
            base,
            ["- 年龄：42（记录日期 2099-01-01）"],
        )
        self.assertIn("## 身份信息", out)
        self.assertIn("年龄：42", out)
        self.assertIn("## 称呼", out)

    def test_inserts_before_next_section(self) -> None:
        base = "# x\n\n## 身份信息\n\n- 旧\n\n## 其它\n\ny\n"
        out = append_user_profile_facts_to_user_md(
            base,
            ["- 新：1（记录日期 2099-01-01）"],
        )
        self.assertLess(out.index("旧"), out.index("新"))
        self.assertLess(out.index("新"), out.index("## 其它"))


class TestToolUserProfileRecord(unittest.TestCase):
    def test_writes_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            try:
                user = root / "USER.md"
                user.write_text("# u\n", encoding="utf-8")
                msg = tool_user_profile_record(
                    root,
                    [{"label": "年龄", "value": "42"}],
                )
                self.assertTrue(msg.startswith("OK"))
                body = user.read_text(encoding="utf-8")
                self.assertIn("年龄", body)
                self.assertIn("42", body)
            finally:
                shutdown_memory_store(root, timeout_s=5.0)

    def test_execute_empty_items_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            try:
                (root / "USER.md").write_text("# u\n", encoding="utf-8")
                out = execute_tool_call_blocking(
                    root,
                    "user_profile_record",
                    json.dumps({"items": []}, ensure_ascii=False),
                )
                self.assertIn("ERROR", out)
            finally:
                shutdown_memory_store(root, timeout_s=5.0)


class TestToolUpdateChatSettings(unittest.TestCase):
    def test_update_and_read_chat_output_format_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            msg = tool_update_chat_settings(
                root,
                '必须输出 JSON: {"reply":"..."}',
            )
            self.assertTrue(msg.startswith("OK"))
            got = read_chat_output_format_prompt(root)
            self.assertEqual(got, '必须输出 JSON: {"reply":"..."}')

    def test_execute_rejects_empty_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = execute_tool_call_blocking(
                root,
                "tool_update_chat_settings",
                json.dumps({"output_format_prompt": "  "}, ensure_ascii=False),
            )
            self.assertIn("ERROR", out)


if __name__ == "__main__":
    unittest.main()
