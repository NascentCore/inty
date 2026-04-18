"""inner_tick_schedule 与 transcript 合成行标志（`is_transcript_real_user_message` 等）。"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from inty_v2_repl.inner_tick_schedule import (
    inner_tick_enabled_from_env,
    next_inner_tick_wait_seconds,
)
from inty_v2_repl.models import (
    REPL_PRESENCE_USER_TEXT_ONLINE,
    ChatMessage,
    is_transcript_real_user_message,
)


def _write_transcript(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )


class TestInnerTickSchedule(unittest.TestCase):
    def test_env_unset_defaults_enabled(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(inner_tick_enabled_from_env())

    def test_inner_tick_enabled_explicit_off(self) -> None:
        with patch.dict(
            os.environ, {"INTY_V2_PROTO_INNER_TICK_ENABLED": "0"}, clear=True
        ):
            self.assertFalse(inner_tick_enabled_from_env())

    def test_old_heartbeat_env_does_not_toggle_inner_tick(self) -> None:
        with patch.dict(os.environ, {"INTY_V2_PROTO_HEARTBEAT": "0"}, clear=True):
            self.assertTrue(inner_tick_enabled_from_env())

    def test_disabled_returns_large_wait(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "transcript.jsonl").write_text("", encoding="utf-8")
            with patch.dict(
                os.environ, {"INTY_V2_PROTO_INNER_TICK_ENABLED": "0"}, clear=True
            ):
                w = next_inner_tick_wait_seconds(root, last_inner_fire_monotonic=None)
            self.assertGreater(w, 86400.0 * 10)

    def test_short_transcript_poll_wait(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_transcript(
                root / "transcript.jsonl",
                [
                    {
                        "role": "user",
                        "content": "hi",
                        "ts": "2026-01-01T00:00:00+00:00",
                        "uuid": "a",
                    },
                ],
            )
            with patch.dict(os.environ, {}, clear=True):
                w = next_inner_tick_wait_seconds(root, last_inner_fire_monotonic=None)
            self.assertGreater(w, 0.0)
            self.assertLess(w, 86400.0)

    def test_none_last_fire_when_ready_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_transcript(
                root / "transcript.jsonl",
                [
                    {
                        "role": "user",
                        "content": "hi",
                        "ts": "2026-01-01T00:00:00+00:00",
                        "uuid": "a",
                    },
                    {
                        "role": "assistant",
                        "content": "hello",
                        "ts": "2026-01-01T00:00:01+00:00",
                        "uuid": "b",
                    },
                ],
            )
            with patch.dict(os.environ, {}, clear=True):
                w = next_inner_tick_wait_seconds(root, last_inner_fire_monotonic=None)
            self.assertLessEqual(w, 0.0)

    def test_ready_when_assistant_last_and_min_gap_elapsed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_transcript(
                root / "transcript.jsonl",
                [
                    {
                        "role": "user",
                        "content": "hi",
                        "ts": "2026-01-01T00:00:00+00:00",
                        "uuid": "a",
                    },
                    {
                        "role": "assistant",
                        "content": "hello",
                        "ts": "2026-01-01T00:00:01+00:00",
                        "uuid": "b",
                    },
                ],
            )
            with patch.dict(
                os.environ,
                {"INTY_V2_PROTO_INNER_TICK_MIN_GAP_SEC": "1"},
                clear=False,
            ):
                w = next_inner_tick_wait_seconds(
                    root, last_inner_fire_monotonic=1000.0, now_monotonic=2000.0
                )
            self.assertLessEqual(w, 0.0)

    def test_min_gap_blocks_immediate_repeat(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_transcript(
                root / "transcript.jsonl",
                [
                    {
                        "role": "user",
                        "content": "hi",
                        "ts": "2026-01-01T00:00:00+00:00",
                        "uuid": "a",
                    },
                    {
                        "role": "assistant",
                        "content": "hello",
                        "ts": "2026-01-01T00:00:01+00:00",
                        "uuid": "b",
                    },
                ],
            )
            with patch.dict(
                os.environ,
                {"INTY_V2_PROTO_INNER_TICK_MIN_GAP_SEC": "300"},
                clear=False,
            ):
                w = next_inner_tick_wait_seconds(
                    root, last_inner_fire_monotonic=1000.0, now_monotonic=1005.0
                )
            self.assertGreater(w, 0.0)


class TestTranscriptFlags(unittest.TestCase):
    def test_repl_online_ack_not_counted_as_real_user(self) -> None:
        m = ChatMessage(
            role="user",
            content="（会话已恢复…）",
            ts="2026-01-01T00:00:00+00:00",
            repl_online_ack=True,
        )
        self.assertFalse(is_transcript_real_user_message(m))

    def test_inner_tick_user_not_real_user(self) -> None:
        m = ChatMessage(
            role="user",
            content="（内在…）",
            ts="2026-01-01T00:00:00+00:00",
            inner_tick=True,
        )
        self.assertFalse(is_transcript_real_user_message(m))

    def test_trailing_repl_online_still_allows_inner_tick_when_assistant_last(
        self,
    ) -> None:
        """presence 行截断后末条仍为 assistant 时应可触发 inner tick。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_transcript(
                root / "transcript.jsonl",
                [
                    {
                        "role": "user",
                        "content": "hi",
                        "ts": "2026-01-01T12:00:00+00:00",
                        "uuid": "a",
                    },
                    {
                        "role": "assistant",
                        "content": "hello",
                        "ts": "2026-01-01T12:00:01+00:00",
                        "uuid": "b",
                    },
                    {
                        "role": "user",
                        "content": REPL_PRESENCE_USER_TEXT_ONLINE,
                        "ts": "2026-01-01T12:00:02+00:00",
                        "uuid": "c",
                        "presence": "repl_online",
                    },
                ],
            )
            with patch.dict(
                os.environ,
                {"INTY_V2_PROTO_INNER_TICK_MIN_GAP_SEC": "1"},
                clear=False,
            ):
                w = next_inner_tick_wait_seconds(
                    root, last_inner_fire_monotonic=1000.0, now_monotonic=2000.0
                )
            self.assertLessEqual(w, 0.0)
