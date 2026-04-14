"""transcript_for_llm_turn：普通轮与心跳共用尾部窗口。"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.inty_v2_repl.models import (
    TRANSCRIPT_WINDOW_MAX_MESSAGES,
    ChatMessage,
    load_transcript,
    transcript_for_llm_turn,
    undo_trailing_repl_online_presence_line,
)


def _msg(i: int) -> ChatMessage:
    role = "user" if i % 2 == 0 else "assistant"
    return ChatMessage(
        role=role,
        content=str(i),
        ts="2026-01-01T00:00:00+00:00",
        uuid=f"u{i}",
    )


class TestTranscriptForLlmTurn(unittest.TestCase):
    def test_long_list_truncates_tail(self) -> None:
        n = TRANSCRIPT_WINDOW_MAX_MESSAGES + 10
        loaded = [_msg(i) for i in range(n)]
        out = transcript_for_llm_turn(loaded)
        self.assertEqual(len(out), TRANSCRIPT_WINDOW_MAX_MESSAGES)
        self.assertEqual(out[0].content, str(n - TRANSCRIPT_WINDOW_MAX_MESSAGES))

    def test_short_list_unchanged(self) -> None:
        loaded = [_msg(0), _msg(1)]
        out = transcript_for_llm_turn(loaded)
        self.assertEqual(out, loaded)

    def test_undo_trailing_repl_online_removes_last_line(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "transcript.jsonl"
            row0 = {"role": "user", "content": "hi", "ts": "2026-01-01T00:00:00Z"}
            row1 = {
                "role": "user",
                "content": "x",
                "ts": "2026-01-01T00:00:01Z",
                "presence": "repl_online",
            }
            p.write_text(
                json.dumps(row0, ensure_ascii=False)
                + "\n"
                + json.dumps(row1, ensure_ascii=False)
                + "\n",
                encoding="utf-8",
            )
            self.assertTrue(undo_trailing_repl_online_presence_line(p))
            loaded = load_transcript(p)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].content, "hi")


if __name__ == "__main__":
    unittest.main()
