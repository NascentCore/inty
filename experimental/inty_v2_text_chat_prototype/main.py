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
from experimental.inty_v2_text_chat_prototype.client import OpenRouterInvalidJsonError

load_prototype_dotenv()

from app.core.repl_input.sleep_chunk import clamp_sleep_seconds
from app.core.repl_input.stdin_queue import spawn_stdin_line_reader

from experimental.inty_v2_text_chat_prototype.bootstrap import (
    ensure_workspace_skeleton,
    init_workspace as bootstrap_init_workspace,
    read_package_template_text,
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
    is_workspace_bootstrap_complete,
    is_workspace_transcript_empty,
    needs_startup_profile_inquiry,
    needs_workspace_template_bootstrap,
    repl_heartbeat_suppressed_for_workspace_bootstrap,
    run_turn,
)
from experimental.inty_v2_text_chat_prototype.tool_background import (
    pop_output_events_nowait,
)
from experimental.inty_v2_text_chat_prototype.schedule_queue import (
    mark_task_fired,
    next_due_wait_seconds,
    mark_task_retry,
    pop_due_task_events_nowait,
    scheduled_task_synthetic_user_text,
    start_schedule_scheduler,
    stop_schedule_scheduler,
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


class _ReplBootstrapPhaseComplete(Exception):
    pass


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


def _process_due_schedule_events(
    ws: Path,
    *,
    run_turn_sync: Callable[[str], str],
) -> None:
    if repl_heartbeat_suppressed_for_workspace_bootstrap(ws):
        return
    events = pop_due_task_events_nowait(workspace=ws)
    for ev in events:
        synthetic_user = scheduled_task_synthetic_user_text(
            task_text=ev.task_text,
            exec_time_utc=ev.exec_time_utc,
        )
        t0 = time.perf_counter()
        try:
            out = run_turn_sync(synthetic_user)
        except Exception as exc:
            mark_task_retry(ws, ev.task_id, str(exc))
            logger.exception(
                "repl schedule task failed ws={} task_id={} error={}",
                ws.name,
                ev.task_id,
                exc,
            )
            continue
        mark_task_fired(ws, ev.task_id)
        print(
            f"[{_local_ts_str()}] schedule-task {int((time.perf_counter() - t0) * 1000)}ms "
            f"(task={ev.task_id[:8]})"
        )
        print(out)
        print("> ", end="", flush=True)


def _next_idle_wait_seconds(*, ws: Path, heartbeat: bool) -> float:
    waits: list[float] = []
    if heartbeat:
        waits.append(next_heartbeat_wait_seconds(ws, heartbeat_enabled=heartbeat))
    due_wait = next_due_wait_seconds(ws)
    if due_wait is not None:
        waits.append(due_wait)
    if not waits:
        return 1.0
    return min(waits)


def _next_due_wait_seconds_only(ws: Path) -> float | None:
    return next_due_wait_seconds(ws)


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


def _print_openrouter_invalid_json_retry_hint() -> None:
    print(f"[{_local_ts_str()}] LLM API 临时异常（上游返回非 JSON），请重试。")


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
    exit_when_bootstrap_complete: bool = False,
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
            try:
                out = run_turn_sync(cur)
            except OpenRouterInvalidJsonError as exc:
                logger.warning("repl turn recovered from invalid OpenRouter JSON: {}", exc)
                _print_openrouter_invalid_json_retry_hint()
                print("> ", end="", flush=True)
                try:
                    item = pending.get_nowait()
                except queue.Empty:
                    return True
                if item is None:
                    print()
                    return False
                cur, cur_echoed = item
                continue
            _print_assistant_reply(out, time.perf_counter() - t0)
            _drain_async_tool_events(ws)
            if exit_when_bootstrap_complete and is_workspace_bootstrap_complete(ws):
                raise _ReplBootstrapPhaseComplete
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
    exit_when_bootstrap_complete: bool = False,
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
        exit_when_bootstrap_complete=exit_when_bootstrap_complete,
    )


def _daemon_run_user_turn_and_drain_queue(
    ws: Path,
    line_queue: queue.Queue[tuple[str, bool] | None],
    first_line: str,
    *,
    debug_print_system: bool,
    first_line_already_echoed: bool = False,
    exit_when_bootstrap_complete: bool = False,
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
        exit_when_bootstrap_complete=exit_when_bootstrap_complete,
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


def _posix_drain_after_heartbeat(
    ws: Path,
    pending: queue.Queue[tuple[str, bool] | None],
    m: str,
    ev: bool,
    *,
    debug_print_system: bool,
    exit_when_bootstrap_complete: bool,
) -> bool:
    return _posix_run_user_turn_and_drain_queue(
        ws,
        pending,
        m,
        debug_print_system=debug_print_system,
        first_line_already_echoed=ev,
        exit_when_bootstrap_complete=exit_when_bootstrap_complete,
    )


def _repl_interactive_loop_posix(
    ws: Path,
    *,
    debug_print_system: bool,
    heartbeat: bool,
    exit_when_bootstrap_complete: bool = False,
) -> None:
    pending: queue.Queue[tuple[str, bool] | None] = queue.Queue()
    stdin_fd = sys.stdin.fileno()
    print("> ", end="", flush=True)

    while True:
        _drain_async_tool_events_in_waiting_loop(ws)
        _process_due_schedule_events(
            ws,
            run_turn_sync=lambda text: _run_turn_with_stdin_pump(
                ws,
                pending,
                user_text=text,
                heartbeat_turn=False,
                debug_print_system=debug_print_system,
            ),
        )
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
            try:
                if not _posix_run_user_turn_and_drain_queue(
                    ws,
                    pending,
                    line,
                    debug_print_system=debug_print_system,
                    first_line_already_echoed=echoed,
                    exit_when_bootstrap_complete=exit_when_bootstrap_complete,
                ):
                    break
            except _ReplBootstrapPhaseComplete:
                return
            continue

        hb_on = heartbeat and not repl_heartbeat_suppressed_for_workspace_bootstrap(ws)
        if hb_on:
            wait = _next_idle_wait_seconds(ws=ws, heartbeat=True)
            if wait <= 0.0:
                hb_wait = next_heartbeat_wait_seconds(ws, heartbeat_enabled=True)
                if hb_wait > 0.0:
                    # Due schedule event should run first; do not force a heartbeat turn.
                    continue
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
                try:
                    if not _consume_pending_after_heartbeat(
                        pending,
                        drain_user_lines=lambda m, ev: _posix_drain_after_heartbeat(
                            ws,
                            pending,
                            m,
                            ev,
                            debug_print_system=debug_print_system,
                            exit_when_bootstrap_complete=exit_when_bootstrap_complete,
                        ),
                    ):
                        break
                except _ReplBootstrapPhaseComplete:
                    return
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
            due_wait = _next_due_wait_seconds_only(ws)
            if due_wait is None:
                line = _readline_main_sync()
                if line is None:
                    print()
                    break
            else:
                sleep_s = clamp_sleep_seconds(
                    due_wait,
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

        if line.strip() in ("quit", "exit", "q"):
            break
        if not line.strip():
            print("> ", end="", flush=True)
            continue
        try:
            if not _posix_run_user_turn_and_drain_queue(
                ws,
                pending,
                line,
                debug_print_system=debug_print_system,
                first_line_already_echoed=False,
                exit_when_bootstrap_complete=exit_when_bootstrap_complete,
            ):
                break
        except _ReplBootstrapPhaseComplete:
            return


def _repl_interactive_loop_daemon(
    ws: Path,
    *,
    debug_print_system: bool,
    heartbeat: bool,
    exit_when_bootstrap_complete: bool = False,
) -> None:
    """Windows / 非 TTY：沿用守护线程读 stdin（无法在主线程 select）。"""
    line_queue, _ = spawn_stdin_line_reader()
    print("> ", end="", flush=True)

    while True:
        _drain_async_tool_events_in_waiting_loop(ws)
        _process_due_schedule_events(
            ws,
            run_turn_sync=lambda text: asyncio.run(
                run_turn(
                    ws,
                    text,
                    heartbeat_turn=False,
                    debug_print_system=debug_print_system,
                    llm_trace=True,
                )
            ),
        )
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
            try:
                if not _daemon_run_user_turn_and_drain_queue(
                    ws,
                    line_queue,
                    line,
                    debug_print_system=debug_print_system,
                    first_line_already_echoed=echoed,
                    exit_when_bootstrap_complete=exit_when_bootstrap_complete,
                ):
                    break
            except _ReplBootstrapPhaseComplete:
                return
            continue

        hb_on = heartbeat and not repl_heartbeat_suppressed_for_workspace_bootstrap(ws)
        if hb_on:
            wait = _next_idle_wait_seconds(ws=ws, heartbeat=True)
            if wait <= 0.0:
                hb_wait = next_heartbeat_wait_seconds(ws, heartbeat_enabled=True)
                if hb_wait > 0.0:
                    continue
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
                try:
                    if not _consume_pending_after_heartbeat(
                        line_queue,
                        drain_user_lines=lambda m, ev: _daemon_run_user_turn_and_drain_queue(
                            ws,
                            line_queue,
                            m,
                            debug_print_system=debug_print_system,
                            first_line_already_echoed=ev,
                            exit_when_bootstrap_complete=exit_when_bootstrap_complete,
                        ),
                    ):
                        break
                except _ReplBootstrapPhaseComplete:
                    return
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
            due_wait = _next_due_wait_seconds_only(ws)
            if due_wait is None:
                item = line_queue.get()
            else:
                sleep_s = clamp_sleep_seconds(
                    due_wait,
                    min_seconds=0.05,
                    max_seconds=HEARTBEAT_MAX_SLEEP_CHUNK_SEC,
                )
                try:
                    item = line_queue.get(timeout=sleep_s)
                except queue.Empty:
                    continue

        if item is None:
            print()
            break
        line, echoed = item
        if line.strip() in ("quit", "exit", "q"):
            break
        if not line.strip():
            print("> ", end="", flush=True)
            continue
        try:
            if not _daemon_run_user_turn_and_drain_queue(
                ws,
                line_queue,
                line,
                debug_print_system=debug_print_system,
                first_line_already_echoed=echoed,
                exit_when_bootstrap_complete=exit_when_bootstrap_complete,
            ):
                break
        except _ReplBootstrapPhaseComplete:
            return


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
    exit_when_bootstrap_complete: bool = False,
) -> None:
    """
    长耗时 turn（如生图）期间仍可读入下一行：在 TTY + POSIX 上由主线程 select+readline 泵入队列，
    `run_turn` 放在工作线程；否则退回守护线程读 stdin。
    """
    if _use_posix_stdin_pump():
        _repl_interactive_loop_posix(
            ws,
            debug_print_system=debug_print_system,
            heartbeat=heartbeat,
            exit_when_bootstrap_complete=exit_when_bootstrap_complete,
        )
    else:
        _repl_interactive_loop_daemon(
            ws,
            debug_print_system=debug_print_system,
            heartbeat=heartbeat,
            exit_when_bootstrap_complete=exit_when_bootstrap_complete,
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
    """从包内 templates/ 拷贝 IDENTITY/SOUL/USER/MEMORY/BOOSTRAP，并创建空 transcript、memory/ 与 memory/daily/、context.json。"""
    _init_proto_logging(path, log_file, no_log_file)
    try:
        bootstrap_init_workspace(path)
    finally:
        _flush_and_shutdown_memory_store(path.resolve())


_SYNTH_USER_BOOTSTRAP_AGENT_DEFAULT = "SYNTH_USER_BOOTSTRAP_AGENT_DEFAULT.md"
_SYNTH_USER_REPL_STARTUP_PROFILE_INQUIRY = "SYNTH_USER_REPL_STARTUP_PROFILE_INQUIRY.md"


def _default_bootstrap_user_message() -> str:
    return read_package_template_text(_SYNTH_USER_BOOTSTRAP_AGENT_DEFAULT)


def _repl_bootstrap_opening_user_stub() -> str:
    """首轮 template bootstrap：opening 指令在 system，本行仅占位 user 角色并写入 transcript。"""
    return "（用户尚未输入。请依 system 中首轮场景与问句规则先开口。）"


def _repl_startup_profile_inquiry_user_message() -> str:
    return read_package_template_text(_SYNTH_USER_REPL_STARTUP_PROFILE_INQUIRY)


def _repl_run_startup_opening_turn(
    ws: Path,
    *,
    user_text: str,
    debug_print_system: bool,
    recovery_label: str,
    inject_repl_bootstrap_opening_system: bool = False,
) -> bool:
    print(f"[{_local_ts_str()}] {_preview_line(user_text)}")
    t0 = time.perf_counter()
    try:
        out = asyncio.run(
            run_turn(
                ws,
                user_text,
                debug_print_system=debug_print_system,
                llm_trace=True,
                inject_repl_bootstrap_opening_system=inject_repl_bootstrap_opening_system,
            )
        )
    except OpenRouterInvalidJsonError as exc:
        logger.warning(
            "{} recovered from invalid OpenRouter JSON: {}",
            recovery_label,
            exc,
        )
        _print_openrouter_invalid_json_retry_hint()
        print("> ", end="", flush=True)
        return False
    _print_assistant_reply(out, time.perf_counter() - t0)
    _drain_async_tool_events(ws)
    print("> ", end="", flush=True)
    return True


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
    """Agentic 工具循环：按 templates/BOOSTRAP.md 用 LLM + 文件工具初始化工作区。"""
    _init_proto_logging(workspace, log_file, no_log_file)
    _configure_llm_trace_for_workspace(workspace)
    logger.debug("cli bootstrap_agent ws={}", workspace.resolve())
    user = (
        message
        if (message is not None and message.strip())
        else _default_bootstrap_user_message()
    )

    def _on_tool(name: str, args: str) -> None:
        if not verbose_tools:
            return
        preview = args if len(args) <= 400 else args[:400] + "..."
        print(f"[tool] {name} {preview}")

    try:
        ensure_workspace_skeleton(workspace)
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
        start_schedule_scheduler(ws)
        logger.debug("cli repl start ws={}", ws.resolve())
        ensure_workspace_skeleton(ws)
        if needs_workspace_template_bootstrap(ws):
            logger.debug(
                "repl startup branch=template_bootstrap_fill (BOOSTRAPED missing, stubs)"
            )
            if not _repl_run_startup_opening_turn(
                ws,
                user_text=_repl_bootstrap_opening_user_stub(),
                debug_print_system=debug_print_system,
                recovery_label="repl startup template_bootstrap",
                inject_repl_bootstrap_opening_system=True,
            ):
                return
        elif needs_startup_profile_inquiry(ws):
            logger.debug(
                "repl startup branch=startup_profile_inquiry (empty transcript, stub profile)"
            )
            if not _repl_run_startup_opening_turn(
                ws,
                user_text=_repl_startup_profile_inquiry_user_message(),
                debug_print_system=debug_print_system,
                recovery_label="repl startup profile inquiry",
            ):
                return
        else:
            logger.debug("repl startup branch=interactive (ready for user input)")

        while not is_workspace_bootstrap_complete(ws):
            logger.debug("repl bootstrap_gate before full_interactive")
            if is_workspace_transcript_empty(ws):
                ok = _repl_run_startup_opening_turn(
                    ws,
                    user_text=_repl_bootstrap_opening_user_stub(),
                    debug_print_system=debug_print_system,
                    recovery_label="repl bootstrap_gate opening",
                    inject_repl_bootstrap_opening_system=True,
                )
                if not ok:
                    return
            if is_workspace_bootstrap_complete(ws):
                break
            print(
                "[初始化] 须在工作区根目录创建空文件 BOOSTRAPED 后才能进入日常对话。"
                " 可继续在此完成初始化，或运行 bootstrap_agent；输入 quit 退出。",
                flush=True,
            )
            _repl_interactive_loop(
                ws,
                debug_print_system=debug_print_system,
                heartbeat=False,
                exit_when_bootstrap_complete=True,
            )
            if not is_workspace_bootstrap_complete(ws):
                return

        hb = _repl_heartbeat_enabled(
            cli_enable=repl_heartbeat,
            cli_disable=no_repl_heartbeat,
        )
        logger.debug("repl interactive heartbeat_enabled={}", hb)
        _repl_interactive_loop(ws, debug_print_system=debug_print_system, heartbeat=hb)
    finally:
        stop_schedule_scheduler(ws)
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
