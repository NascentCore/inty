"""Cyclopts 入口：init-workspace / repl / once。"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Annotated

from cyclopts import App, Parameter

from .bootstrap import init_workspace as bootstrap_init_workspace
from .orchestrator import run_turn


def _default_workspace() -> Path:
    return Path(__file__).resolve().parent / "workspace"


def _local_ts_str() -> str:
    dt = datetime.now().astimezone()
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + dt.strftime(" %z")


def _print_assistant_reply(out: str, elapsed_s: float) -> None:
    ms = elapsed_s * 1000
    print(f"[{_local_ts_str()}] {ms:.0f}ms")
    print(out)


app = App(
    name="inty-v2-text-chat-prototype",
    help="INTY v2 本地文本聊天原型（文件持久化，无 HTTP/DB）。",
)


@app.command
def init_workspace(
    path: Annotated[
        Path,
        Parameter(name="--path", help="要创建的 workspace 目录路径"),
    ],
) -> None:
    """写入 IDENTITY/SOUL/USER/MEMORY、空 transcript、memory/.gitkeep、context.json。"""
    bootstrap_init_workspace(path)


@app.command
def repl(
    workspace: Annotated[
        Path | None,
        Parameter(name="--workspace", help="workspace 根目录；默认包内 workspace/"),
    ] = None,
    debug_print_system: Annotated[
        bool,
        Parameter(name="--debug-print-system", help="打印本轮 system prompt"),
    ] = False,
) -> None:
    """交互循环，输入 quit 或 EOF 结束。"""
    ws = workspace or _default_workspace()
    while True:
        try:
            line = input("> ")
        except EOFError:
            print()
            break
        if line.strip() in ("quit", "exit", "q"):
            break
        if not line.strip():
            continue
        t0 = time.perf_counter()
        out = run_turn(ws, line, debug_print_system=debug_print_system)
        _print_assistant_reply(out, time.perf_counter() - t0)


@app.command
def once(
    message: Annotated[str, Parameter(help="用户本轮输入")],
    workspace: Annotated[
        Path | None,
        Parameter(name="--workspace", help="workspace 根目录；默认包内 workspace/"),
    ] = None,
    debug_print_system: Annotated[
        bool,
        Parameter(name="--debug-print-system", help="打印本轮 system prompt"),
    ] = False,
) -> None:
    """单轮对话。"""
    ws = workspace or _default_workspace()
    t0 = time.perf_counter()
    out = run_turn(ws, message, debug_print_system=debug_print_system)
    _print_assistant_reply(out, time.perf_counter() - t0)


if __name__ == "__main__":
    app()
