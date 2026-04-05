"""陪伴心跳调度：transcript 节奏与冷却。"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from experimental.inty_v2_text_chat_prototype.heartbeat_schedule import (
    heartbeat_enabled_from_env,
    next_heartbeat_wait_seconds,
)
from experimental.inty_v2_text_chat_prototype.models import (
    REPL_PRESENCE_USER_TEXT_ONLINE,
    ChatMessage,
    is_transcript_real_user_message,
)


def _write_transcript(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )


class TestHeartbeatSchedule(unittest.TestCase):
    def test_repl_online_ack_not_counted_as_real_user(self) -> None:
        m = ChatMessage(
            role="user",
            content="（会话已恢复…）",
            ts="2026-01-01T00:00:00+00:00",
            repl_online_ack=True,
        )
        self.assertFalse(is_transcript_real_user_message(m))

    def test_env_unset_defaults_heartbeat_enabled(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(heartbeat_enabled_from_env())

    def test_disabled_returns_large_wait(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "transcript.jsonl").write_text("", encoding="utf-8")
            with patch.dict(
                os.environ, {"INTY_V2_PROTO_HEARTBEAT": "0"}, clear=True
            ):
                w = next_heartbeat_wait_seconds(root)
            self.assertGreater(w, 86400.0 * 10)

    def test_short_transcript_no_fire(self) -> None:
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
            with patch.dict(os.environ, {"INTY_V2_PROTO_HEARTBEAT": "1"}, clear=False):
                w = next_heartbeat_wait_seconds(root)
            self.assertGreater(w, 86400.0)

    def test_ready_when_assistant_stale(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            t_user = t0.isoformat()
            t_asst = (t0 + timedelta(seconds=1)).isoformat()
            _write_transcript(
                root / "transcript.jsonl",
                [
                    {"role": "user", "content": "hi", "ts": t_user, "uuid": "a"},
                    {
                        "role": "assistant",
                        "content": "hello",
                        "ts": t_asst,
                        "uuid": "b",
                    },
                ],
            )
            now = t0 + timedelta(seconds=3600)
            with patch.dict(
                os.environ,
                {
                    "INTY_V2_PROTO_HEARTBEAT": "1",
                    "INTY_V2_PROTO_HEARTBEAT_IDLE_SEC": "10",
                },
                clear=False,
            ):
                w = next_heartbeat_wait_seconds(root, now=now)
            self.assertLessEqual(w, 0.0)

    def test_trailing_repl_online_does_not_block_heartbeat_when_assistant_last(self) -> None:
        """末尾 repl_online 行不应视为「最后一轮停在 user」而禁用心跳。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            t_user = t0.isoformat()
            t_asst = (t0 + timedelta(seconds=1)).isoformat()
            t_pres = (t0 + timedelta(seconds=2)).isoformat()
            _write_transcript(
                root / "transcript.jsonl",
                [
                    {"role": "user", "content": "hi", "ts": t_user, "uuid": "a"},
                    {
                        "role": "assistant",
                        "content": "hello",
                        "ts": t_asst,
                        "uuid": "b",
                    },
                    {
                        "role": "user",
                        "content": REPL_PRESENCE_USER_TEXT_ONLINE,
                        "ts": t_pres,
                        "uuid": "c",
                        "presence": "repl_online",
                    },
                ],
            )
            now = t0 + timedelta(seconds=3600)
            with patch.dict(
                os.environ,
                {
                    "INTY_V2_PROTO_HEARTBEAT": "1",
                    "INTY_V2_PROTO_HEARTBEAT_IDLE_SEC": "10",
                },
                clear=False,
            ):
                w = next_heartbeat_wait_seconds(root, now=now)
            self.assertLessEqual(w, 0.0)

    def test_explicit_heartbeat_true_without_env_matches_enabled(self) -> None:
        """REPL `--repl-heartbeat` 不设环境变量时仍应能调度心跳。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            t_user = t0.isoformat()
            t_asst = (t0 + timedelta(seconds=1)).isoformat()
            _write_transcript(
                root / "transcript.jsonl",
                [
                    {"role": "user", "content": "hi", "ts": t_user, "uuid": "a"},
                    {
                        "role": "assistant",
                        "content": "hello",
                        "ts": t_asst,
                        "uuid": "b",
                    },
                ],
            )
            now = t0 + timedelta(seconds=3600)
            with patch.dict(os.environ, {}, clear=True):
                w = next_heartbeat_wait_seconds(root, now=now, heartbeat_enabled=True)
            self.assertLessEqual(w, 0.0)

    def test_explicit_heartbeat_false_overrides_env(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with patch.dict(os.environ, {"INTY_V2_PROTO_HEARTBEAT": "1"}, clear=False):
                w = next_heartbeat_wait_seconds(root, heartbeat_enabled=False)
            self.assertGreater(w, 86400.0 * 10)

    def test_min_gap_after_previous_heartbeat(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            rows = [
                {"role": "user", "content": "a", "ts": base.isoformat(), "uuid": "1"},
                {
                    "role": "assistant",
                    "content": "b",
                    "ts": (base + timedelta(seconds=1)).isoformat(),
                    "uuid": "2",
                },
                {
                    "role": "user",
                    "content": "hb",
                    "ts": (base + timedelta(seconds=120)).isoformat(),
                    "uuid": "3",
                    "heartbeat": True,
                },
                {
                    "role": "assistant",
                    "content": "ping",
                    "ts": (base + timedelta(seconds=121)).isoformat(),
                    "uuid": "4",
                },
            ]
            _write_transcript(root / "transcript.jsonl", rows)
            now = base + timedelta(seconds=200)
            with patch.dict(
                os.environ,
                {
                    "INTY_V2_PROTO_HEARTBEAT": "1",
                    "INTY_V2_PROTO_HEARTBEAT_IDLE_SEC": "5",
                    "INTY_V2_PROTO_HEARTBEAT_MIN_GAP_SEC": "600",
                },
                clear=False,
            ):
                w = next_heartbeat_wait_seconds(root, now=now)
            self.assertGreater(w, 100.0)

    def test_blocks_second_heartbeat_without_new_user_input(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            rows = [
                {
                    "role": "user",
                    "content": "你好",
                    "ts": base.isoformat(),
                    "uuid": "u1",
                },
                {
                    "role": "assistant",
                    "content": "在呢",
                    "ts": (base + timedelta(seconds=1)).isoformat(),
                    "uuid": "a1",
                },
                {
                    "role": "user",
                    "content": "hb1",
                    "ts": (base + timedelta(minutes=5)).isoformat(),
                    "uuid": "u2",
                    "heartbeat": True,
                },
                {
                    "role": "assistant",
                    "content": "我在这",
                    "ts": (base + timedelta(minutes=5, seconds=1)).isoformat(),
                    "uuid": "a2",
                },
            ]
            _write_transcript(root / "transcript.jsonl", rows)
            now = base + timedelta(hours=2)
            with patch.dict(
                os.environ,
                {
                    "INTY_V2_PROTO_HEARTBEAT": "1",
                    "INTY_V2_PROTO_HEARTBEAT_IDLE_SEC": "10",
                    "INTY_V2_PROTO_HEARTBEAT_MIN_GAP_SEC": "10",
                },
                clear=False,
            ):
                w = next_heartbeat_wait_seconds(root, now=now)
            self.assertGreater(w, 86400.0 * 10)

    def test_allows_heartbeat_again_after_real_user_message(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            rows = [
                {
                    "role": "user",
                    "content": "你好",
                    "ts": base.isoformat(),
                    "uuid": "u1",
                },
                {
                    "role": "assistant",
                    "content": "在呢",
                    "ts": (base + timedelta(seconds=1)).isoformat(),
                    "uuid": "a1",
                },
                {
                    "role": "user",
                    "content": "hb1",
                    "ts": (base + timedelta(minutes=5)).isoformat(),
                    "uuid": "u2",
                    "heartbeat": True,
                },
                {
                    "role": "assistant",
                    "content": "我在这",
                    "ts": (base + timedelta(minutes=5, seconds=1)).isoformat(),
                    "uuid": "a2",
                },
                {
                    "role": "user",
                    "content": "我回来了",
                    "ts": (base + timedelta(minutes=50)).isoformat(),
                    "uuid": "u3",
                },
                {
                    "role": "assistant",
                    "content": "欢迎回来",
                    "ts": (base + timedelta(minutes=50, seconds=1)).isoformat(),
                    "uuid": "a3",
                },
            ]
            _write_transcript(root / "transcript.jsonl", rows)
            now = base + timedelta(hours=2)
            with patch.dict(
                os.environ,
                {
                    "INTY_V2_PROTO_HEARTBEAT": "1",
                    "INTY_V2_PROTO_HEARTBEAT_IDLE_SEC": "10",
                    "INTY_V2_PROTO_HEARTBEAT_MIN_GAP_SEC": "10",
                },
                clear=False,
            ):
                w = next_heartbeat_wait_seconds(root, now=now)
            self.assertLessEqual(w, 0.0)

    def test_min_user_quiet_sec_zero_allows_immediate_by_user_quiet_gate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            rows = [
                {"role": "user", "content": "hi", "ts": base.isoformat(), "uuid": "u1"},
                {
                    "role": "assistant",
                    "content": "hello",
                    "ts": (base + timedelta(seconds=1)).isoformat(),
                    "uuid": "a1",
                },
            ]
            _write_transcript(root / "transcript.jsonl", rows)
            now = base + timedelta(seconds=20)
            with patch.dict(
                os.environ,
                {
                    "INTY_V2_PROTO_HEARTBEAT": "1",
                    "INTY_V2_PROTO_HEARTBEAT_IDLE_SEC": "5",
                    "INTY_V2_PROTO_HEARTBEAT_MIN_USER_QUIET_SEC": "0",
                },
                clear=False,
            ):
                w = next_heartbeat_wait_seconds(root, now=now)
            self.assertLessEqual(w, 0.0)

    def test_min_user_quiet_sec_large_blocks_even_when_idle_due(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            rows = [
                {"role": "user", "content": "hi", "ts": base.isoformat(), "uuid": "u1"},
                {
                    "role": "assistant",
                    "content": "hello",
                    "ts": (base + timedelta(seconds=1)).isoformat(),
                    "uuid": "a1",
                },
            ]
            _write_transcript(root / "transcript.jsonl", rows)
            now = base + timedelta(seconds=300)
            with patch.dict(
                os.environ,
                {
                    "INTY_V2_PROTO_HEARTBEAT": "1",
                    "INTY_V2_PROTO_HEARTBEAT_IDLE_SEC": "5",
                    "INTY_V2_PROTO_HEARTBEAT_MIN_USER_QUIET_SEC": "1000",
                },
                clear=False,
            ):
                w = next_heartbeat_wait_seconds(root, now=now)
            self.assertGreater(w, 600.0)


if __name__ == "__main__":
    unittest.main()
