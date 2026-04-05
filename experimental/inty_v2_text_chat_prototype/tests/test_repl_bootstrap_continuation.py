"""REPL：BOOSTRAPED 完成前每轮助手回复后仅打印 `>`，不自动注入 synthetic continuation。"""

from __future__ import annotations

import queue
import sys
from pathlib import Path
from unittest.mock import patch

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.main import _repl_drain_user_turns


def test_drain_user_turns_does_not_chain_bootstrap_continuation(tmp_path: Path) -> None:
    pending: queue.Queue[tuple[str, bool] | None] = queue.Queue()
    calls: list[str] = []

    def sync(cur: str) -> str:
        calls.append(cur)
        assert cur == "hi"
        return "opening"

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
    assert calls == ["hi"]
    assert not (tmp_path / "BOOSTRAPED").is_file()
