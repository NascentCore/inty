"""REPL：workspace_write_file 白名单。"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.workspace_init_tools import (
    REPL_WRITABLE_RELATIVE_PATHS,
    execute_tool_call_blocking,
)


class TestReplWriteAllowlist(unittest.TestCase):
    def test_allows_soul_md(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "SOUL.md").write_text("a\n", encoding="utf-8")
            out = execute_tool_call_blocking(
                root,
                "workspace_write_file",
                json.dumps(
                    {"relative_path": "SOUL.md", "content": "b\n"},
                    ensure_ascii=False,
                ),
                write_allowlist=REPL_WRITABLE_RELATIVE_PATHS,
            )
            self.assertTrue(out.startswith("OK"))
            self.assertEqual((root / "SOUL.md").read_text(encoding="utf-8"), "b\n")

    def test_allows_capabilities_md(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "CAPABILITIES.md").write_text("a\n", encoding="utf-8")
            out = execute_tool_call_blocking(
                root,
                "workspace_write_file",
                json.dumps(
                    {"relative_path": "CAPABILITIES.md", "content": "b\n"},
                    ensure_ascii=False,
                ),
                write_allowlist=REPL_WRITABLE_RELATIVE_PATHS,
            )
            self.assertTrue(out.startswith("OK"))
            self.assertEqual(
                (root / "CAPABILITIES.md").read_text(encoding="utf-8"), "b\n"
            )

    def test_blocks_transcript(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = execute_tool_call_blocking(
                root,
                "workspace_write_file",
                json.dumps(
                    {"relative_path": "transcript.jsonl", "content": "{}\n"},
                    ensure_ascii=False,
                ),
                write_allowlist=REPL_WRITABLE_RELATIVE_PATHS,
            )
            self.assertIn("ERROR", out)
            self.assertIn("transcript.jsonl", out)

    def test_bootstrap_unrestricted_without_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = execute_tool_call_blocking(
                root,
                "workspace_write_file",
                json.dumps(
                    {"relative_path": "nested/x.txt", "content": "z"},
                    ensure_ascii=False,
                ),
                write_allowlist=None,
            )
            self.assertTrue(out.startswith("OK"))
            self.assertEqual(
                (root / "nested" / "x.txt").read_text(encoding="utf-8"), "z"
            )


if __name__ == "__main__":
    unittest.main()
