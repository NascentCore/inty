"""load_transcript：跳过非法行；ts 接受 timestamp 别名；bootstrap 写 transcript 校验。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.models import load_transcript
from inty_v2_text_chat_prototype.workspace_init_tools import tool_workspace_write_file


class TestLoadTranscriptLenient(unittest.TestCase):
    def test_skips_invalid_rows_keeps_valid(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "transcript.jsonl"
            p.write_text(
                '{"timestamp":"2025-04-03T00:00:00Z","content":"初始化开始"}\n'
                '{"role":"assistant","content":"hi","ts":"2025-04-03T00:00:01Z"}\n',
                encoding="utf-8",
            )
            rows = load_transcript(p)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].role, "assistant")
            self.assertEqual(rows[0].content, "hi")

    def test_timestamp_alias_with_role(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "transcript.jsonl"
            p.write_text(
                '{"role":"system","content":"x","timestamp":"2026-01-01T00:00:00Z"}\n',
                encoding="utf-8",
            )
            rows = load_transcript(p)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].ts, "2026-01-01T00:00:00Z")

    def test_bootstrap_write_rejects_transcript_without_role(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bad = (
                '{"timestamp":"2025-04-03T00:00:00Z","content":"初始化开始"}\n'
            )
            out = tool_workspace_write_file(root, "transcript.jsonl", bad)
            self.assertTrue(out.startswith("ERROR:"))
            self.assertFalse((root / "transcript.jsonl").is_file())

    def test_bootstrap_write_accepts_timestamp_alias(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            good = (
                '{"role":"system","content":"m",'
                '"timestamp":"2026-01-01T00:00:00Z"}\n'
            )
            out = tool_workspace_write_file(root, "transcript.jsonl", good)
            self.assertTrue(out.startswith("OK wrote"))
            rows = load_transcript(root / "transcript.jsonl")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].role, "system")


if __name__ == "__main__":
    unittest.main()
