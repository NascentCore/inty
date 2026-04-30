"""REPL full-duplex: in-flight wait (mocked select), line queueing, EOF abort."""

from __future__ import annotations

import os
import threading
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from unittest.mock import MagicMock, patch

# ``import inty_v2_repl``：见同目录 conftest（将 ``tools/`` 加入 path）
from inty_v2_repl.main import (
    _duplex_inflight_degraded_wait,
    _duplex_inflight_posix_select_wait,
    _repl_interactive_backend_ws_loop,
)


def test_inflight_posix_select_wait_queues_full_lines() -> None:
    """While a turn Future is in flight, any readable stdin in ``select`` appends a full line to ``pending``."""
    import time  # noqa: PLC0415

    pending: deque[str] = deque()
    rpipe, wpipe = os.pipe()
    _stdin = 9
    n_call = 0
    read_idx = 0
    lines = ["first\n", "second\n"]

    def _readline() -> str:
        nonlocal read_idx
        if read_idx < len(lines):
            s = lines[read_idx]
            read_idx += 1
            return s
        return ""

    def _sel(rl, wl, xl, t) -> tuple[list[int], list, list]:  # noqa: ANN001
        nonlocal n_call
        n_call += 1
        if n_call <= 2:
            return ([_stdin], [], [])
        return ([], [], [])

    with ThreadPoolExecutor(max_workers=1) as ex:
        fut: Future = ex.submit(
            lambda: (time.sleep(0.15), "done")[-1]
        )
        try:
            _duplex_inflight_posix_select_wait(
                fut,
                rpipe,
                pending,
                stdin_fd=_stdin,
                readline_fn=_readline,
                select_fn=_sel,
                poll_sec=0.01,
            )
        finally:
            for fd in (rpipe, wpipe):
                try:
                    os.close(fd)
                except OSError:
                    pass
    assert fut.result() == "done"
    assert list(pending) == ["first", "second"]


def test_inflight_degraded_wait_completes() -> None:
    with ThreadPoolExecutor(max_workers=1) as ex:
        fut: Future = ex.submit(lambda: 42)
        _duplex_inflight_degraded_wait(fut)
    assert fut.result() == 42


def test_eof_inflight_calls_bridge_stop_without_assistant_print() -> None:
    evt = threading.Event()
    bridge = MagicMock()

    def send_turn(_agent_id: str, _text: str) -> tuple[str, dict]:
        evt.wait(timeout=120)
        return "never-print", {}

    bridge.send_turn.side_effect = send_turn

    def stop() -> None:
        evt.set()

    bridge.stop.side_effect = stop

    with patch(
        "inty_v2_repl.main._readline_backend_ws_with_sideband",
        return_value="hello",
    ):
        with patch(
            "inty_v2_repl.main._use_posix_tty_duplex_select",
            return_value=True,
        ):
            with patch(
                "inty_v2_repl.main._duplex_inflight_posix_select_wait",
                side_effect=EOFError,
            ):
                with patch(
                    "inty_v2_repl.main._print_assistant_reply"
                ) as print_reply:
                    _repl_interactive_backend_ws_loop(bridge, "agent-id")

    bridge.stop.assert_called()
    print_reply.assert_not_called()
