"""OpenRouter 非 JSON 响应重试与 REPL 容错回归。"""

from __future__ import annotations

import importlib
import json
import queue
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.client import (
    OpenRouterInvalidJsonError,
    create_chat_completion,
)
from inty_v2_text_chat_prototype.main import (
    OpenRouterInvalidJsonError as ReplOpenRouterInvalidJsonError,
)
from inty_v2_text_chat_prototype.main import _print_openrouter_invalid_json_retry_hint
from inty_v2_text_chat_prototype.main import _repl_drain_user_turns
from inty_v2_text_chat_prototype.main import repl


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
            model="google/gemini-2.5-flash",
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
                model="google/gemini-2.5-flash",
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

    def _run_turn_sync(cur: str) -> tuple[str, dict[str, str]]:
        called["n"] += 1
        if called["n"] == 1:
            raise ReplOpenRouterInvalidJsonError("broken upstream body")
        return f"assistant:{cur}", {}

    with (
        patch(
            "inty_v2_text_chat_prototype.main._local_ts_str", return_value="2026-04-03"
        ),
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


def test_client_exception_identity_shared_between_import_paths() -> None:
    pkg_mod = importlib.import_module("inty_v2_text_chat_prototype.client")
    exp_mod = importlib.import_module("tools.inty_v2_repl.client")
    assert pkg_mod is exp_mod
    assert (
        pkg_mod.OpenRouterInvalidJsonError
        is exp_mod.OpenRouterInvalidJsonError
        is OpenRouterInvalidJsonError
    )


def test_repl_startup_bootstrap_branch_handles_openrouter_invalid_json() -> None:
    with (
        patch(
            "inty_v2_text_chat_prototype.main.is_workspace_initialized",
            return_value=False,
        ),
        patch(
            "inty_v2_text_chat_prototype.main.run_workspace_bootstrap_loop"
        ) as mock_boot,
        patch("inty_v2_text_chat_prototype.main._init_proto_logging"),
        patch("inty_v2_text_chat_prototype.main._configure_llm_trace_for_workspace"),
        patch("inty_v2_text_chat_prototype.main._flush_and_shutdown_memory_store"),
        patch("inty_v2_text_chat_prototype.main._repl_interactive_loop") as mock_loop,
        patch(
            "inty_v2_text_chat_prototype.main._print_openrouter_invalid_json_retry_hint"
        ) as mock_hint,
    ):
        mock_boot.side_effect = OpenRouterInvalidJsonError("bad upstream body")
        repl(workspace=Path("/tmp/ws-a"))
    mock_hint.assert_called_once_with()
    mock_loop.assert_not_called()


def test_repl_startup_profile_branch_handles_openrouter_invalid_json() -> None:
    mock_run_turn = AsyncMock(
        side_effect=OpenRouterInvalidJsonError("bad upstream body")
    )
    with (
        patch(
            "inty_v2_text_chat_prototype.main.is_workspace_initialized",
            return_value=True,
        ),
        patch(
            "inty_v2_text_chat_prototype.main.needs_startup_profile_inquiry",
            return_value=True,
        ),
        patch("inty_v2_text_chat_prototype.main.run_turn", mock_run_turn),
        patch("inty_v2_text_chat_prototype.main._init_proto_logging"),
        patch("inty_v2_text_chat_prototype.main._configure_llm_trace_for_workspace"),
        patch("inty_v2_text_chat_prototype.main._flush_and_shutdown_memory_store"),
        patch("inty_v2_text_chat_prototype.main._repl_interactive_loop") as mock_loop,
        patch(
            "inty_v2_text_chat_prototype.main._print_openrouter_invalid_json_retry_hint"
        ) as mock_hint,
    ):
        repl(workspace=Path("/tmp/ws-b"))
    mock_hint.assert_called_once_with()
    mock_loop.assert_not_called()


def test_print_openrouter_invalid_json_retry_hint() -> None:
    with (
        patch(
            "inty_v2_text_chat_prototype.main._local_ts_str", return_value="2026-04-03"
        ),
        patch("builtins.print") as mock_print,
    ):
        _print_openrouter_invalid_json_retry_hint()
    mock_print.assert_called_once_with(
        "[2026-04-03] LLM API 临时异常（上游返回非 JSON），请重试。"
    )


def test_repl_online_ack_runtime_error_undoes_presence_and_skips_loop() -> None:
    """Online-ack 非 OpenRouter JSON 类失败时撤销 repl_online，不进入交互循环，不写 repl_offline。"""
    mock_run_turn = AsyncMock(
        side_effect=RuntimeError(
            "async chat front timed out after 1s (trace_id=x); retry"
        )
    )
    mock_append = MagicMock()
    mock_undo = MagicMock(return_value=True)
    ws = Path("/tmp/ws-repl-online-ack-fail")
    with (
        patch(
            "inty_v2_text_chat_prototype.main.is_workspace_initialized",
            return_value=True,
        ),
        patch(
            "inty_v2_text_chat_prototype.main.needs_startup_profile_inquiry",
            return_value=False,
        ),
        patch("inty_v2_text_chat_prototype.main.run_turn", mock_run_turn),
        patch(
            "inty_v2_text_chat_prototype.main._append_repl_presence_transcript",
            mock_append,
        ),
        patch(
            "inty_v2_text_chat_prototype.main.undo_trailing_repl_online_presence_line",
            mock_undo,
        ),
        patch("inty_v2_text_chat_prototype.main._init_proto_logging"),
        patch("inty_v2_text_chat_prototype.main._configure_llm_trace_for_workspace"),
        patch("inty_v2_text_chat_prototype.main._log_repl_inner_tick_env"),
        patch("inty_v2_text_chat_prototype.main.start_schedule_scheduler"),
        patch("inty_v2_text_chat_prototype.main._repl_interactive_loop") as mock_loop,
        patch("inty_v2_text_chat_prototype.main._flush_and_shutdown_memory_store"),
        patch("inty_v2_text_chat_prototype.main.stop_schedule_scheduler"),
        patch(
            "inty_v2_text_chat_prototype.main._local_ts_str", return_value="2026-04-05"
        ),
        patch("builtins.print") as mock_print,
    ):
        repl(workspace=ws)
    mock_loop.assert_not_called()
    mock_append.assert_any_call(ws, "repl_online")
    assert all(c[0][1] != "repl_offline" for c in mock_append.call_args_list)
    mock_undo.assert_called_once()
    printed = [c[0][0] for c in mock_print.call_args_list]
    assert any("REPL 上线问候失败" in s for s in printed)
