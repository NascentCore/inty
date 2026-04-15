"""OpenRouter 非 JSON 响应重试回归（本地 client）；repl 仅后端 WebSocket。"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import tools.inty_v2_repl.client
from tools.inty_v2_repl.client import (
    OpenRouterInvalidJsonError,
    create_chat_completion,
)
from tools.inty_v2_repl.main import _print_openrouter_invalid_json_retry_hint


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
    with patch("tools.inty_v2_repl.client.time.sleep", return_value=None):
        resp = create_chat_completion(
            client,
            model="google/gemini-2.5-flash",
            messages_payload=[{"role": "user", "content": "hi"}],
            tools=[],
        )
    assert resp.choices[0].message.content == "ok"
    assert client.chat.completions.calls == 2


def test_create_chat_completion_raises_domain_error_after_max_retries() -> None:
    client = SimpleNamespace(chat=SimpleNamespace(completions=_FlakyCompletions(9)))
    with patch("tools.inty_v2_repl.client.time.sleep", return_value=None):
        try:
            create_chat_completion(
                client,
                model="google/gemini-2.5-flash",
                messages_payload=[{"role": "user", "content": "hi"}],
                tools=[],
            )
            assert False, "expected OpenRouterInvalidJsonError"
        except OpenRouterInvalidJsonError as exc:
            assert "after 3 attempts" in str(exc)
    assert client.chat.completions.calls == 3


def test_client_exception_identity_shared_between_import_paths() -> None:
    pkg_mod = importlib.import_module("tools.inty_v2_repl.client")
    exp_mod = importlib.import_module("inty_v2_text_chat_prototype.client")
    assert pkg_mod is exp_mod
    assert (
        pkg_mod.OpenRouterInvalidJsonError
        is exp_mod.OpenRouterInvalidJsonError
        is OpenRouterInvalidJsonError
    )


def test_print_openrouter_invalid_json_retry_hint() -> None:
    with (
        patch("tools.inty_v2_repl.main.repl_wall_ts_str", return_value="2026-04-03"),
        patch("builtins.print") as mock_print,
    ):
        _print_openrouter_invalid_json_retry_hint()
    mock_print.assert_called_once_with(
        "[2026-04-03] LLM API 临时异常（上游返回非 JSON），请重试。"
    )
