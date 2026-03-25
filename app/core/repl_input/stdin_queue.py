"""
Non-blocking stdin for REPL-style CLIs: lines are read on a daemon thread into a FIFO queue.

Callers can `queue.get(timeout=...)` on the main thread while long work (e.g. LLM turns) runs,
so users may type ahead; lines accumulate until consumed.
"""

from __future__ import annotations

import queue
import sys
import threading
from typing import TextIO


def spawn_stdin_line_reader(
    *,
    stdin: TextIO | None = None,
) -> tuple[queue.Queue[tuple[str, bool] | None], threading.Thread]:
    """
    Start a daemon thread that reads lines from `stdin` (default `sys.stdin`).

    Puts ``(text, False)`` for each line (``False`` = not yet echoed by the consumer).
    Puts ``None`` once when:
    - EOF is read (empty read), or
    - ``readline`` raises ``KeyboardInterrupt``.

    The thread then exits. Consumers should treat ``None`` as end-of-input for the session.
    """
    inp = stdin if stdin is not None else sys.stdin
    q: queue.Queue[tuple[str, bool] | None] = queue.Queue()

    def _run() -> None:
        while True:
            try:
                raw = inp.readline()
            except KeyboardInterrupt:
                q.put(None)
                return
            if raw == "":
                q.put(None)
                return
            q.put((raw.rstrip("\r\n"), False))

    thread = threading.Thread(
        target=_run,
        daemon=True,
        name="repl-input-stdin-line-reader",
    )
    thread.start()
    return q, thread
