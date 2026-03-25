"""Cyclopts 入口：init-workspace / repl / once。"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Annotated

from cyclopts import App, Parameter

# `python main.py` loads this file as __main__ with no package; ensure parent of this
# directory is on sys.path so `inty_v2_text_chat_prototype.*` resolves like `python -m`.
_PKG_DIR = Path(__file__).resolve().parent
if __package__ is None:
    sys.path.insert(0, str(_PKG_DIR.parent))

from inty_v2_text_chat_prototype.bootstrap import init_workspace as bootstrap_init_workspace
from inty_v2_text_chat_prototype.llm_trace import configure_llm_trace_file
from inty_v2_text_chat_prototype.orchestrator import (
    is_workspace_initialized,
    needs_startup_profile_inquiry,
    run_turn,
)
from inty_v2_text_chat_prototype.workspace_init_loop import run_workspace_bootstrap_loop


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
    """写入 IDENTITY/SOUL/USER/MEMORY、空 transcript、memory/ 与 memory/daily/、context.json。"""
    bootstrap_init_workspace(path)


_DEFAULT_BOOTSTRAP_USER = (
    "我们刚选定彼此，我还不是完全体：请你用伴侣的方式，按你的理解把自己安顿好，"
    "跟我自然聊出称呼、你怎么称呼自己、相处上的底线；节奏随我，不必像填设置表。"
    "在你能静默完成的那部分就绪之后，请邀请我一起定义你，并自然地问我愿分享的基本信息（怎么称呼我、希望怎样被称呼等），不要像问卷。"
    "别跟我讲文件夹或配置文件名字；需要默认身份编号时用人话问一句就行。"
    "请你自己完成该完成的事，不要推给我去终端替你初始化。"
)

# repl 自动初始化时传给 agentic 循环的用户消息（不当作 REPL 输入回显）
_REPL_SILENT_INIT_USER_MESSAGE = (
    "用户刚打开对话。你是刚被选中、还没被完全记清的伴侣 AI：先自然打个招呼，"
    "按用户节奏聊，需要时用工具静默记下；不要对用户提工作区、文件名或清单式提问。"
    "当你内部该落盘的部分就绪后，在本轮结束前邀请用户一起定义你（称呼、你怎么称呼自己、相处底线），"
    "并自然地询问关于对方的基本信息（怎么称呼对方、希望怎样被称呼等），像聊天而不是填表。"
)

# 已初始化但 transcript 仍为空、且 IDENTITY/USER 仍像占位：启动时由助手先开口（写入 transcript）
_REPL_STARTUP_PROFILE_INQUIRY_USER_MESSAGE = (
    "（用户刚打开对话，尚未输入。）请你先开口：用伴侣语气自然发问，"
    "了解你希望自己的称呼、你怎么称呼自己、以及关于对方的基本信息（怎么称呼对方等）；"
    "不要提工作区或文件名，不要像问卷。"
)


@app.command
def bootstrap_agent(
    workspace: Annotated[
        Path,
        Parameter(name="--workspace", help="要初始化的 workspace 根目录"),
    ],
    message: Annotated[
        str | None,
        Parameter(
            name="--message",
            help="用户补充说明；省略则使用内置默认初始化请求",
        ),
    ] = None,
    verbose_tools: Annotated[
        bool,
        Parameter(name="--verbose-tools", help="打印每轮调用的工具名与参数摘要"),
    ] = False,
    llm_trace_file: Annotated[
        Path | None,
        Parameter(
            name="--llm-trace-file",
            help="将每轮 chat.completions 的请求/响应摘要追加写入该文件（便于 tail -f）",
        ),
    ] = None,
) -> None:
    """Agentic 工具循环：按 _ws2/BOOSTRAP.md 用 LLM + 文件工具初始化工作区。"""
    configure_llm_trace_file(llm_trace_file)
    trace_on = llm_trace_file is not None
    user = message if (message is not None and message.strip()) else _DEFAULT_BOOTSTRAP_USER

    def _on_tool(name: str, args: str) -> None:
        if not verbose_tools:
            return
        preview = args if len(args) <= 400 else args[:400] + "..."
        print(f"[tool] {name} {preview}")

    out = run_workspace_bootstrap_loop(
        workspace,
        user,
        on_tool=_on_tool if verbose_tools else None,
        llm_trace=trace_on,
    )
    if out:
        print(out)


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
    llm_trace_file: Annotated[
        Path | None,
        Parameter(
            name="--llm-trace-file",
            help="将每轮 chat.completions 的请求/响应摘要追加写入该文件（便于 tail -f）",
        ),
    ] = None,
) -> None:
    """交互循环，输入 quit 或 EOF 结束。"""
    configure_llm_trace_file(llm_trace_file)
    trace_on = llm_trace_file is not None
    ws = workspace or _default_workspace()
    if not is_workspace_initialized(ws):
        t0 = time.perf_counter()
        out = run_workspace_bootstrap_loop(
            ws, _REPL_SILENT_INIT_USER_MESSAGE, llm_trace=trace_on
        )
        _print_assistant_reply(out, time.perf_counter() - t0)
    elif needs_startup_profile_inquiry(ws):
        t0 = time.perf_counter()
        out = run_turn(
            ws,
            _REPL_STARTUP_PROFILE_INQUIRY_USER_MESSAGE,
            debug_print_system=debug_print_system,
            llm_trace=trace_on,
        )
        _print_assistant_reply(out, time.perf_counter() - t0)
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
        out = run_turn(
            ws, line, debug_print_system=debug_print_system, llm_trace=trace_on
        )
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
    llm_trace_file: Annotated[
        Path | None,
        Parameter(
            name="--llm-trace-file",
            help="将每轮 chat.completions 的请求/响应摘要追加写入该文件（便于 tail -f）",
        ),
    ] = None,
) -> None:
    """单轮对话。"""
    configure_llm_trace_file(llm_trace_file)
    trace_on = llm_trace_file is not None
    ws = workspace or _default_workspace()
    t0 = time.perf_counter()
    out = run_turn(
        ws,
        message,
        debug_print_system=debug_print_system,
        defer_memory_update=False,
        llm_trace=trace_on,
    )
    _print_assistant_reply(out, time.perf_counter() - t0)


if __name__ == "__main__":
    app()
