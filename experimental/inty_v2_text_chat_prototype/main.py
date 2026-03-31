"""Cyclopts 入口：init-workspace / repl / once。"""

from __future__ import annotations

import asyncio
import queue
import select
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Annotated, Callable

from cyclopts import App, Parameter
from loguru import logger

# `python main.py` loads this file as __main__ with no package; ensure parent of this
# directory is on sys.path so `inty_v2_text_chat_prototype.*` resolves like `python -m`.
# Repo root enables `import app` (e.g. Fal z-image tool → app.core.images.fal).
_PKG_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PKG_DIR.parent.parent
if __package__ is None:
    sys.path.insert(0, str(_PKG_DIR.parent))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from experimental.inty_v2_text_chat_prototype.client import load_prototype_dotenv

load_prototype_dotenv()

from app.core.repl_input.sleep_chunk import clamp_sleep_seconds
from app.core.repl_input.stdin_queue import spawn_stdin_line_reader

from experimental.inty_v2_text_chat_prototype.bootstrap import (
    init_workspace as bootstrap_init_workspace,
)
from experimental.inty_v2_text_chat_prototype.llm_trace import configure_llm_trace_file
from experimental.inty_v2_text_chat_prototype.proto_log import (
    configure_proto_log,
    resolve_proto_log_file,
)

from experimental.inty_v2_text_chat_prototype.heartbeat_schedule import (
    HEARTBEAT_MAX_SLEEP_CHUNK_SEC,
    next_heartbeat_wait_seconds,
)
from experimental.inty_v2_text_chat_prototype.orchestrator import (
    is_workspace_initialized,
    needs_startup_profile_inquiry,
    run_turn,
)
from experimental.inty_v2_text_chat_prototype.tool_background import (
    pop_output_events_nowait,
)
from experimental.inty_v2_text_chat_prototype.memory_store_registry import (
    flush_memory_store,
    shutdown_memory_store,
)
from experimental.inty_v2_text_chat_prototype.jsonl_db_store import (
    flush_jsonl_db_store,
    shutdown_jsonl_db_store,
)
from experimental.inty_v2_text_chat_prototype.workspace_init_loop import (
    run_workspace_bootstrap_loop,
)


def _default_workspace() -> Path:
    return Path(__file__).resolve().parent / "workspace"


def _local_ts_str() -> str:
    dt = datetime.now().astimezone()
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + dt.strftime(" %z")


def _print_assistant_reply(out: str, elapsed_s: float) -> None:
    ms = elapsed_s * 1000
    print(f"[{_local_ts_str()}] {ms:.0f}ms")
    print(out)


def _drain_async_tool_events(ws: Path) -> None:
    events = pop_output_events_nowait(workspace=ws)
    for ev in events:
        print(
            f"[{_local_ts_str()}] async-tool {ev.elapsed_ms}ms "
            f"(user={ev.user_msg_uuid[:8]} asst={ev.assistant_msg_uuid[:8]})"
        )
        print(ev.text)
        print("> ", end="", flush=True)


def _drain_async_tool_events_in_waiting_loop(ws: Path) -> None:
    _drain_async_tool_events(ws)


def _init_proto_logging(
    workspace: Path,
    log_file: Path | None,
    no_log_file: bool,
) -> None:
    """默认仅 <workspace>/inty_v2.log（不写 stderr，免干扰 REPL）；--no-log-file 则仅 stderr。"""
    resolved = resolve_proto_log_file(
        workspace, explicit=log_file, no_log_file=no_log_file
    )
    configure_proto_log(resolved)
    logger.info(
        "inty_v2 proto logging file={}",
        str(resolved) if resolved is not None else "(stderr only)",
    )


def _configure_llm_trace_for_workspace(root: Path) -> None:
    """Append-only JSONL：每轮 chat.completions 请求/响应摘要，固定 `<workspace>/llm_trace.jsonl`。"""
    configure_llm_trace_file(root.resolve() / "llm_trace.jsonl")


def _flush_and_shutdown_memory_store(root: Path) -> None:
    flush_memory_store(root, timeout_s=5.0)
    flush_jsonl_db_store(timeout_s=5.0)
    shutdown_memory_store(root, timeout_s=5.0)
    shutdown_jsonl_db_store(timeout_s=5.0)


def _use_posix_stdin_pump() -> bool:
    """TTY + POSIX：主线程 select stdin，避免「仅守护线程读 stdin」在部分集成终端里长耗时 turn 期间无法输入。"""
    if sys.platform == "win32":
        return False
    try:
        return sys.stdin.isatty()
    except (OSError, ValueError):
        return False


def _readline_main_sync() -> str | None:
    try:
        raw = sys.stdin.readline()
    except KeyboardInterrupt:
        return None
    if raw == "":
        return None
    return raw.rstrip("\r\n")


def _repl_drain_user_turns(
    first_line: str,
    *,
    run_turn_sync: Callable[[str], str],
    pending: queue.Queue[tuple[str, bool] | None],
    ws: Path,
    first_line_already_echoed: bool = False,
) -> bool:
    """
    跑一轮 user turn，然后连续消费 `pending` 里在本轮之前/期间积压的行（均得到助手回复），
    再回到「等 stdin / 心跳」。若返回 False，REPL 应退出。

    `tuple[str, bool]` 为 (文本, 是否已在 stdin 泵阶段打印过时间戳与 `> `)；为 True 时不再重复打印，
    以免长耗时 turn（如生图）期间用户已输入的行看起来「卡住无回显」。
    """
    cur = first_line
    cur_echoed = first_line_already_echoed
    while True:
        if cur.strip() in ("quit", "exit", "q"):
            return False
        if not cur.strip():
            print("> ", end="", flush=True)
        else:
            if not cur_echoed:
                print(f"[{_local_ts_str()}] {cur}")
                logger.debug(
                    "repl interactive_turn line_chars={} preview={}",
                    len(cur),
                    _preview_line(cur),
                )
                print("> ", end="", flush=True)
            t0 = time.perf_counter()
            out = run_turn_sync(cur)
            _print_assistant_reply(out, time.perf_counter() - t0)
            _drain_async_tool_events(ws)
            print("> ", end="", flush=True)

        try:
            item = pending.get_nowait()
        except queue.Empty:
            return True
        if item is None:
            print()
            return False
        cur, cur_echoed = item


def _posix_run_user_turn_and_drain_queue(
    ws: Path,
    pending: queue.Queue[tuple[str, bool] | None],
    first_line: str,
    *,
    debug_print_system: bool,
    first_line_already_echoed: bool = False,
) -> bool:
    def _sync(cur: str) -> str:
        return _run_turn_with_stdin_pump(
            ws,
            pending,
            user_text=cur,
            heartbeat_turn=False,
            debug_print_system=debug_print_system,
        )

    return _repl_drain_user_turns(
        first_line,
        run_turn_sync=_sync,
        pending=pending,
        ws=ws,
        first_line_already_echoed=first_line_already_echoed,
    )


def _daemon_run_user_turn_and_drain_queue(
    ws: Path,
    line_queue: queue.Queue[tuple[str, bool] | None],
    first_line: str,
    *,
    debug_print_system: bool,
    first_line_already_echoed: bool = False,
) -> bool:
    def _sync(cur: str) -> str:
        return asyncio.run(
            run_turn(ws, cur, debug_print_system=debug_print_system, llm_trace=True)
        )

    return _repl_drain_user_turns(
        first_line,
        run_turn_sync=_sync,
        pending=line_queue,
        ws=ws,
        first_line_already_echoed=first_line_already_echoed,
    )


def _consume_pending_after_heartbeat(
    pending: queue.Queue[tuple[str, bool] | None],
    *,
    drain_user_lines: Callable[[str, bool], bool],
) -> bool:
    """心跳回合结束后：若队列里已有用户行则继续回复。返回 False 表示应结束 REPL。"""
    try:
        more = pending.get_nowait()
    except queue.Empty:
        return True
    if more is None:
        print()
        return False
    line, echoed = more
    if not line.strip():
        print("> ", end="", flush=True)
        return True
    return drain_user_lines(line, echoed)


def _run_turn_with_stdin_pump(
    ws: Path,
    pending: queue.Queue[tuple[str, bool] | None],
    *,
    user_text: str,
    heartbeat_turn: bool,
    debug_print_system: bool,
) -> str:
    """
    `run_turn` 在工作线程里跑；主线程用 select+readline 把后续行写入 `pending`，
    供本轮结束后的循环消费（FIFO）。
    """
    done = threading.Event()
    result: dict[str, str] = {}
    exc: list[BaseException] = []

    def worker() -> None:
        try:
            result["out"] = asyncio.run(
                run_turn(
                    ws,
                    user_text,
                    heartbeat_turn=heartbeat_turn,
                    debug_print_system=debug_print_system,
                    llm_trace=True,
                )
            )
        except BaseException as e:
            exc.append(e)
        finally:
            done.set()

    t = threading.Thread(
        target=worker,
        name="inty-v2-run-turn",
        daemon=True,
    )
    t.start()
    stdin_fd = sys.stdin.fileno()
    # Do not print (async tool output, etc.) while the user may be mid-line in the TTY
    # line discipline: interleaved stdout corrupts the screen vs kernel buffer, so
    # backspace appears to "not delete" earlier characters. Only flush async events
    # after a full line is read from stdin, or after the worker finishes.
    while not done.is_set():
        r, _, _ = select.select([stdin_fd], [], [], 0.1)
        if not r:
            continue
        raw = sys.stdin.readline()
        _drain_async_tool_events_in_waiting_loop(ws)
        if raw == "":
            pending.put(None)
        else:
            text = raw.rstrip("\r\n")
            print(f"[{_local_ts_str()}] {text}")
            logger.debug(
                "repl stdin_pump queued line_chars={} preview={}",
                len(text),
                _preview_line(text),
            )
            print("> ", end="", flush=True)
            pending.put((text, True))
    t.join(timeout=3600.0)
    _drain_async_tool_events_in_waiting_loop(ws)
    if exc:
        raise exc[0]
    return result["out"]


def _repl_interactive_loop_posix(
    ws: Path,
    *,
    debug_print_system: bool,
    heartbeat: bool,
) -> None:
    pending: queue.Queue[tuple[str, bool] | None] = queue.Queue()
    stdin_fd = sys.stdin.fileno()
    print("> ", end="", flush=True)

    while True:
        _drain_async_tool_events_in_waiting_loop(ws)
        try:
            item = pending.get_nowait()
        except queue.Empty:
            pass
        else:
            if item is None:
                print()
                break
            line, echoed = item
            if not line.strip():
                print("> ", end="", flush=True)
                continue
            if not _posix_run_user_turn_and_drain_queue(
                ws,
                pending,
                line,
                debug_print_system=debug_print_system,
                first_line_already_echoed=echoed,
            ):
                break
            continue

        if heartbeat:
            wait = next_heartbeat_wait_seconds(ws, heartbeat_enabled=heartbeat)
            if wait <= 0.0:
                logger.debug("repl heartbeat branch=fire wait_s={:.1f}", wait)
                t0 = time.perf_counter()
                out = _run_turn_with_stdin_pump(
                    ws,
                    pending,
                    user_text="",
                    heartbeat_turn=True,
                    debug_print_system=debug_print_system,
                )
                _print_assistant_reply(out, time.perf_counter() - t0)
                print("> ", end="", flush=True)
                if not _consume_pending_after_heartbeat(
                    pending,
                    drain_user_lines=lambda m, ev: _posix_run_user_turn_and_drain_queue(
                        ws,
                        pending,
                        m,
                        debug_print_system=debug_print_system,
                        first_line_already_echoed=ev,
                    ),
                ):
                    break
                continue

            sleep_s = clamp_sleep_seconds(
                wait,
                min_seconds=0.05,
                max_seconds=HEARTBEAT_MAX_SLEEP_CHUNK_SEC,
            )
            r, _, _ = select.select([stdin_fd], [], [], sleep_s)
            if not r:
                continue
            raw = sys.stdin.readline()
            if raw == "":
                print()
                break
            line = raw.rstrip("\r\n")
        else:
            line = _readline_main_sync()
            if line is None:
                print()
                break

        if line.strip() in ("quit", "exit", "q"):
            break
        if not line.strip():
            print("> ", end="", flush=True)
            continue
        if not _posix_run_user_turn_and_drain_queue(
            ws,
            pending,
            line,
            debug_print_system=debug_print_system,
            first_line_already_echoed=False,
        ):
            break


def _repl_interactive_loop_daemon(
    ws: Path,
    *,
    debug_print_system: bool,
    heartbeat: bool,
) -> None:
    """Windows / 非 TTY：沿用守护线程读 stdin（无法在主线程 select）。"""
    line_queue, _ = spawn_stdin_line_reader()
    print("> ", end="", flush=True)

    while True:
        _drain_async_tool_events_in_waiting_loop(ws)
        try:
            item = line_queue.get_nowait()
        except queue.Empty:
            pass
        else:
            if item is None:
                print()
                break
            line, echoed = item
            if not line.strip():
                print("> ", end="", flush=True)
                continue
            if not _daemon_run_user_turn_and_drain_queue(
                ws,
                line_queue,
                line,
                debug_print_system=debug_print_system,
                first_line_already_echoed=echoed,
            ):
                break
            continue

        if heartbeat:
            wait = next_heartbeat_wait_seconds(ws, heartbeat_enabled=heartbeat)
            if wait <= 0.0:
                logger.debug("repl heartbeat branch=fire wait_s={:.1f}", wait)
                t0 = time.perf_counter()
                print("> ", end="", flush=True)
                out = asyncio.run(
                    run_turn(
                        ws,
                        "",
                        heartbeat_turn=True,
                        debug_print_system=debug_print_system,
                        llm_trace=True,
                    )
                )
                _print_assistant_reply(out, time.perf_counter() - t0)
                print("> ", end="", flush=True)
                if not _consume_pending_after_heartbeat(
                    line_queue,
                    drain_user_lines=lambda m, ev: _daemon_run_user_turn_and_drain_queue(
                        ws,
                        line_queue,
                        m,
                        debug_print_system=debug_print_system,
                        first_line_already_echoed=ev,
                    ),
                ):
                    break
                continue

            sleep_s = clamp_sleep_seconds(
                wait,
                min_seconds=0.05,
                max_seconds=HEARTBEAT_MAX_SLEEP_CHUNK_SEC,
            )
            try:
                item = line_queue.get(timeout=sleep_s)
            except queue.Empty:
                continue
        else:
            item = line_queue.get()

        if item is None:
            print()
            break
        line, echoed = item
        if line.strip() in ("quit", "exit", "q"):
            break
        if not line.strip():
            print("> ", end="", flush=True)
            continue
        if not _daemon_run_user_turn_and_drain_queue(
            ws,
            line_queue,
            line,
            debug_print_system=debug_print_system,
            first_line_already_echoed=echoed,
        ):
            break


def _repl_heartbeat_enabled(
    *,
    cli_enable: bool,
    cli_disable: bool,
) -> bool:
    """`--no-repl-heartbeat` 优先；否则 `--repl-heartbeat`；否则读 INTY_V2_PROTO_HEARTBEAT。"""
    from experimental.inty_v2_text_chat_prototype.heartbeat_schedule import (
        heartbeat_enabled_from_env,
    )

    if cli_disable:
        return False
    if cli_enable:
        return True
    return heartbeat_enabled_from_env()


def _repl_interactive_loop(
    ws: Path,
    *,
    debug_print_system: bool,
    heartbeat: bool,
) -> None:
    """
    长耗时 turn（如生图）期间仍可读入下一行：在 TTY + POSIX 上由主线程 select+readline 泵入队列，
    `run_turn` 放在工作线程；否则退回守护线程读 stdin。
    """
    if _use_posix_stdin_pump():
        _repl_interactive_loop_posix(
            ws, debug_print_system=debug_print_system, heartbeat=heartbeat
        )
    else:
        _repl_interactive_loop_daemon(
            ws, debug_print_system=debug_print_system, heartbeat=heartbeat
        )


def _preview_line(s: str, max_len: int = 200) -> str:
    one = s.replace("\n", " ").strip()
    if len(one) <= max_len:
        return one
    return one[: max_len - 1] + "…"


app = App(
    name="inty-v2-text-chat-prototype",
    help="INTY v2 本地文本聊天原型（Memory 主读 + Postgres 异步持久化 + 文件镜像）。",
)


@app.command
def init_workspace(
    path: Annotated[
        Path,
        Parameter(name="--path", help="要创建的 workspace 目录路径"),
    ],
    log_file: Annotated[
        Path | None,
        Parameter(
            name="--log-file",
            help="loguru 文件日志路径；默认 <path>/inty_v2.log；见 --no-log-file",
        ),
    ] = None,
    no_log_file: Annotated[
        bool,
        Parameter(name="--no-log-file", help="不写 inty_v2.log，仅 stderr"),
    ] = False,
) -> None:
    """写入 IDENTITY/SOUL/USER/MEMORY、空 transcript、memory/ 与 memory/daily/、context.json。"""
    _init_proto_logging(path, log_file, no_log_file)
    try:
        bootstrap_init_workspace(path)
    finally:
        _flush_and_shutdown_memory_store(path.resolve())


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
    log_file: Annotated[
        Path | None,
        Parameter(
            name="--log-file",
            help="loguru 文件日志；默认 <workspace>/inty_v2.log",
        ),
    ] = None,
    no_log_file: Annotated[
        bool,
        Parameter(name="--no-log-file", help="不写 inty_v2.log，仅 stderr"),
    ] = False,
) -> None:
    """Agentic 工具循环：按 _ws2/BOOSTRAP.md 用 LLM + 文件工具初始化工作区。"""
    _init_proto_logging(workspace, log_file, no_log_file)
    _configure_llm_trace_for_workspace(workspace)
    logger.debug("cli bootstrap_agent ws={}", workspace.resolve())
    user = (
        message
        if (message is not None and message.strip())
        else _DEFAULT_BOOTSTRAP_USER
    )

    def _on_tool(name: str, args: str) -> None:
        if not verbose_tools:
            return
        preview = args if len(args) <= 400 else args[:400] + "..."
        print(f"[tool] {name} {preview}")

    try:
        out = run_workspace_bootstrap_loop(
            workspace,
            user,
            on_tool=_on_tool if verbose_tools else None,
            llm_trace=True,
        )
        if out:
            print(out)
    finally:
        _flush_and_shutdown_memory_store(workspace.resolve())


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
    log_file: Annotated[
        Path | None,
        Parameter(
            name="--log-file",
            help="loguru 文件日志；默认 <workspace>/inty_v2.log",
        ),
    ] = None,
    no_log_file: Annotated[
        bool,
        Parameter(name="--no-log-file", help="不写 inty_v2.log，仅 stderr"),
    ] = False,
    repl_heartbeat: Annotated[
        bool,
        Parameter(
            name="--repl-heartbeat",
            help="启用空闲陪伴心跳（按 transcript 节奏主动一轮；可配合 INTY_V2_PROTO_HEARTBEAT）",
        ),
    ] = False,
    no_repl_heartbeat: Annotated[
        bool,
        Parameter(
            name="--no-repl-heartbeat",
            help="显式关闭空闲心跳（覆盖环境变量）",
        ),
    ] = False,
) -> None:
    """交互循环，输入 quit 或 EOF 结束。"""
    ws = workspace or _default_workspace()
    try:
        _init_proto_logging(ws, log_file, no_log_file)
        _configure_llm_trace_for_workspace(ws)
        logger.debug("cli repl start ws={}", ws.resolve())
        if not is_workspace_initialized(ws):
            logger.debug(
                "repl startup branch=bootstrap_auto_init (workspace not initialized)"
            )
            t0 = time.perf_counter()
            out = run_workspace_bootstrap_loop(
                ws, _REPL_SILENT_INIT_USER_MESSAGE, llm_trace=True
            )
            _print_assistant_reply(out, time.perf_counter() - t0)
        elif needs_startup_profile_inquiry(ws):
            logger.debug(
                "repl startup branch=startup_profile_inquiry (empty transcript, stub profile)"
            )
            t0 = time.perf_counter()
            out = asyncio.run(
                run_turn(
                    ws,
                    _REPL_STARTUP_PROFILE_INQUIRY_USER_MESSAGE,
                    debug_print_system=debug_print_system,
                    llm_trace=True,
                )
            )
            _print_assistant_reply(out, time.perf_counter() - t0)
        else:
            logger.debug("repl startup branch=interactive (ready for user input)")
        hb = _repl_heartbeat_enabled(
            cli_enable=repl_heartbeat,
            cli_disable=no_repl_heartbeat,
        )
        logger.debug("repl interactive heartbeat_enabled={}", hb)
        _repl_interactive_loop(ws, debug_print_system=debug_print_system, heartbeat=hb)
    finally:
        _flush_and_shutdown_memory_store(ws.resolve())


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
    log_file: Annotated[
        Path | None,
        Parameter(
            name="--log-file",
            help="loguru 文件日志；默认 <workspace>/inty_v2.log",
        ),
    ] = None,
    no_log_file: Annotated[
        bool,
        Parameter(name="--no-log-file", help="不写 inty_v2.log，仅 stderr"),
    ] = False,
) -> None:
    """单轮对话。"""
    ws = workspace or _default_workspace()
    try:
        _init_proto_logging(ws, log_file, no_log_file)
        _configure_llm_trace_for_workspace(ws)
        logger.debug(
            "cli once ws={} message_chars={} preview={}",
            ws.resolve(),
            len(message),
            _preview_line(message, max_len=240),
        )
        t0 = time.perf_counter()
        out = asyncio.run(
            run_turn(
                ws,
                message,
                debug_print_system=debug_print_system,
                defer_memory_update=False,
                llm_trace=True,
            )
        )
        _print_assistant_reply(out, time.perf_counter() - t0)
    finally:
        _flush_and_shutdown_memory_store(ws.resolve())


if __name__ == "__main__":
    app()
