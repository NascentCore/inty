"""OpenRouter 非 JSON 响应重试与 REPL 容错回归。"""

from __future__ import annotations

import json
import queue
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.client import (
    OpenRouterInvalidJsonError,
    create_chat_completion,
)
from inty_v2_text_chat_prototype.main import (
    OpenRouterInvalidJsonError as ReplOpenRouterInvalidJsonError,
)
from inty_v2_text_chat_prototype.main import _repl_drain_user_turns


class _FlakyCompletions:
    def __init__(self, fail_times: int) -> None:
        self._fail_times = fail_times
        self.calls = 0

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.calls += 1
        if self.calls <= self._fail_times:
            raise json.JSONDecodeError("Expecting value", "", 0)
        msg = SimpleNamespace(content="ok", tool_calls=[])
        ch = SimpleNamespace(message=msg, finish_reason="stop")
        return SimpleNamespace(choices=[ch], usage=None)


def test_create_chat_completion_retries_after_json_decode_error() -> None:
    client = SimpleNamespace(chat=SimpleNamespace(completions=_FlakyCompletions(1)))
    with patch("inty_v2_text_chat_prototype.client.time.sleep", return_value=None):
        resp = create_chat_completion(
            client,
            model="deepseek/deepseek-v3.2",
            messages_payload=[{"role": "user", "content": "hi"}],
            tools=[],
        )
    assert resp.choices[0].message.content == "ok"
    assert client.chat.completions.calls == 2


def test_create_chat_completion_raises_domain_error_after_max_retries() -> None:
    client = SimpleNamespace(chat=SimpleNamespace(completions=_FlakyCompletions(9)))
    with patch("inty_v2_text_chat_prototype.client.time.sleep", return_value=None):
        try:
            create_chat_completion(
                client,
                model="deepseek/deepseek-v3.2",
                messages_payload=[{"role": "user", "content": "hi"}],
                tools=[],
            )
            assert False, "expected OpenRouterInvalidJsonError"
        except OpenRouterInvalidJsonError as exc:
            assert "after 3 attempts" in str(exc)
    assert client.chat.completions.calls == 3


def test_repl_drain_user_turns_recovers_from_openrouter_invalid_json_error() -> None:
    pending: queue.Queue[tuple[str, bool] | None] = queue.Queue()
    pending.put(("第二条消息", False))
    called = {"n": 0}

    def _run_turn_sync(cur: str) -> str:
        called["n"] += 1
        if called["n"] == 1:
            raise ReplOpenRouterInvalidJsonError("broken upstream body")
        return f"assistant:{cur}"

    with (
        patch("inty_v2_text_chat_prototype.main._local_ts_str", return_value="2026-04-03"),
        patch("builtins.print"),
    ):
        keep_running = _repl_drain_user_turns(
            "第一条消息",
            run_turn_sync=_run_turn_sync,
            pending=pending,
            ws=Path("/tmp/unused"),
            first_line_already_echoed=False,
        )
    assert keep_running is True
    assert called["n"] == 2
