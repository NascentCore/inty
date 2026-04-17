"""workspace_read_file：max_chars 与全文读取。"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_repl.workspace_init_tools import (
    WORKSPACE_READ_FILE_MAX_CHARS_CAP,
    execute_tool_call_blocking,
    tool_workspace_read_file,
)


class TestWorkspaceReadFile(unittest.TestCase):
    def test_memory_md_file_read_from_memory_store(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "USER.md").write_text("# USER\n", encoding="utf-8")
            out = execute_tool_call_blocking(
                root,
                "workspace_read_file",
                json.dumps({"relative_path": "USER.md"}, ensure_ascii=False),
            )
            self.assertEqual(out, "# USER\n")

    def test_full_file_omit_max_chars(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.txt").write_text("hello", encoding="utf-8")
            out = execute_tool_call_blocking(
                root,
                "workspace_read_file",
                json.dumps({"relative_path": "a.txt"}, ensure_ascii=False),
            )
            self.assertEqual(out, "hello")

    def test_prefix_truncation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "b.txt").write_text("abcdefghij", encoding="utf-8")
            out = execute_tool_call_blocking(
                root,
                "workspace_read_file",
                json.dumps(
                    {"relative_path": "b.txt", "max_chars": 4}, ensure_ascii=False
                ),
            )
            self.assertTrue(out.startswith("abcd"))
            self.assertIn("truncated", out)

    def test_max_chars_covers_whole_file_no_truncation_marker(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "c.txt").write_text("xy", encoding="utf-8")
            out = execute_tool_call_blocking(
                root,
                "workspace_read_file",
                json.dumps(
                    {"relative_path": "c.txt", "max_chars": 10}, ensure_ascii=False
                ),
            )
            self.assertEqual(out, "xy")
            self.assertNotIn("truncated", out)

    def test_invalid_max_chars_zero(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "d.txt").write_text("z", encoding="utf-8")
            out = execute_tool_call_blocking(
                root,
                "workspace_read_file",
                json.dumps(
                    {"relative_path": "d.txt", "max_chars": 0}, ensure_ascii=False
                ),
            )
            self.assertIn("ERROR", out)

    def test_invalid_max_chars_above_cap(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "e.txt").write_text("z", encoding="utf-8")
            out = execute_tool_call_blocking(
                root,
                "workspace_read_file",
                json.dumps(
                    {
                        "relative_path": "e.txt",
                        "max_chars": WORKSPACE_READ_FILE_MAX_CHARS_CAP + 1,
                    },
                    ensure_ascii=False,
                ),
            )
            self.assertIn("ERROR", out)

    def test_tool_direct_call(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "f.txt").write_text("abc", encoding="utf-8")
            self.assertEqual(
                tool_workspace_read_file(root, "f.txt", max_chars=2),
                "ab\n…[truncated: prefix only; file is longer than max_chars]",
            )


if __name__ == "__main__":
    unittest.main()
