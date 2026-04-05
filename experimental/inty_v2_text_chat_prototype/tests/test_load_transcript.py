"""load_transcript：解析 user/assistant/system；其它 role 行跳过。"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from experimental.inty_v2_text_chat_prototype.file_store import append_line
from experimental.inty_v2_text_chat_prototype.models import ChatMessage, load_transcript


class TestLoadTranscript(unittest.TestCase):
    def test_loads_system_skips_unknown_role(self) -> None:
        rows = [
            {"role": "system", "content": "bootstrap noise", "ts": "t0"},
            {"role": "user", "content": "hi", "ts": "t1"},
            {"role": "assistant", "content": "hey", "ts": "t2"},
            {"role": "tool", "content": "x", "ts": "t9"},
        ]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "transcript.jsonl"
            p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
            loaded = load_transcript(p)
        self.assertEqual(
            loaded,
            [
                ChatMessage(role="system", content="bootstrap noise", ts="t0"),
                ChatMessage(role="user", content="hi", ts="t1"),
                ChatMessage(role="assistant", content="hey", ts="t2"),
            ],
        )

    def test_glued_json_objects_on_one_line(self) -> None:
        a = {"role": "system", "content": "s", "ts": "t0"}
        b = {"role": "assistant", "content": "hi", "ts": "t1"}
        glued = json.dumps(a, ensure_ascii=False) + json.dumps(b, ensure_ascii=False)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "transcript.jsonl"
            p.write_text(glued + "\n", encoding="utf-8")
            loaded = load_transcript(p)
        self.assertEqual(
            loaded,
            [
                ChatMessage(role="system", content="s", ts="t0"),
                ChatMessage(role="assistant", content="hi", ts="t1"),
            ],
        )

    def test_append_line_inserts_newline_before_next_record(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "t.jsonl"
            p.write_text('{"a":1}', encoding="utf-8")
            append_line(p, '{"b":2}')
            self.assertEqual(p.read_text(encoding="utf-8"), '{"a":1}\n{"b":2}\n')


if __name__ == "__main__":
    unittest.main()
