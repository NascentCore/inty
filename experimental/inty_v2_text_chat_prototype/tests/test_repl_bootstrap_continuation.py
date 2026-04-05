"""REPL：缺 BOOSTRAPED 时续跑 synthetic user 与 `run_workspace_bootstrap_loop` 对齐。"""

from __future__ import annotations

import queue
import sys
from pathlib import Path
from unittest.mock import patch

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.main import (
    _repl_drain_bootstrap_continuations_if_needed,
    _repl_drain_user_turns,
)
from inty_v2_text_chat_prototype.workspace_init_loop import (
    WORKSPACE_BOOTSTRAP_MAX_LLM_ROUNDS,
    repl_bootstrap_continue_user_message,
)


def test_continuation_writes_boostraped_on_second_llm_call(tmp_path: Path) -> None:
    calls: list[str] = []

    def sync(text: str) -> str:
        calls.append(text)
        assert text == repl_bootstrap_continue_user_message()
        if len(calls) == 1:
            return "请稍等"
        (tmp_path / "BOOSTRAPED").write_text("", encoding="utf-8")
        return "完成"

    with patch("builtins.print"):
        _repl_drain_bootstrap_continuations_if_needed(tmp_path, sync)

    assert len(calls) == 2
    assert (tmp_path / "BOOSTRAPED").is_file()


def test_continuation_hits_cap_without_boostraped(tmp_path: Path) -> None:
    calls: list[str] = []

    def sync(text: str) -> str:
        calls.append(text)
        return ""

    with patch("builtins.print"):
        _repl_drain_bootstrap_continuations_if_needed(tmp_path, sync)

    assert len(calls) == WORKSPACE_BOOTSTRAP_MAX_LLM_ROUNDS


def test_drain_user_turn_chains_continuation(tmp_path: Path) -> None:
    pending: queue.Queue[tuple[str, bool] | None] = queue.Queue()
    cont = repl_bootstrap_continue_user_message()
    calls: list[str] = []

    def sync(cur: str) -> str:
        calls.append(cur)
        if cur == "hi":
            return "opening"
        assert cur == cont
        (tmp_path / "BOOSTRAPED").write_text("", encoding="utf-8")
        return "done"

    with (
        patch("inty_v2_text_chat_prototype.main._local_ts_str", return_value="ts"),
        patch("builtins.print"),
    ):
        ok = _repl_drain_user_turns(
            "hi",
            run_turn_sync=sync,
            pending=pending,
            ws=tmp_path,
            first_line_already_echoed=False,
        )
    assert ok is True
    assert calls == ["hi", cont]
