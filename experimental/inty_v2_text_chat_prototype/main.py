"""Cyclopts 入口：init-workspace / repl / once。"""

from __future__ import annotations

import asyncio
import os
import queue
import select
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated, Callable

from cyclopts import App, Parameter
from loguru import logger

try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore[misc, assignment]

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
    init_workspace as bootstrap_init_workspace,
)
from experimental.inty_v2_text_chat_prototype.llm_trace import configure_llm_trace_file
from experimental.inty_v2_text_chat_prototype.proto_log import (
    configure_proto_log,
    resolve_proto_log_file,
)

from experimental.inty_v2_text_chat_prototype.inner_tick_schedule import (
    REPL_IDLE_MAX_SLEEP_CHUNK_SEC,
    inner_tick_enabled_from_env,
    next_inner_tick_wait_seconds,
)
from experimental.inty_v2_text_chat_prototype.orchestrator import (
    is_workspace_initialized,
    needs_startup_profile_inquiry,
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
    append_jsonl_with_db,
    flush_jsonl_db_store,
    shutdown_jsonl_db_store,
)
from experimental.inty_v2_text_chat_prototype.models import (
    PresenceSignal,
    REPL_ONLINE_ACK_USER_TEXT,
    REPL_PRESENCE_USER_TEXT_OFFLINE,
    REPL_PRESENCE_USER_TEXT_ONLINE,
    undo_trailing_repl_online_presence_line,
)
from experimental.inty_v2_text_chat_prototype.paths import WorkspacePaths
from experimental.inty_v2_text_chat_prototype.utc import utc_iso_ts
from experimental.inty_v2_text_chat_prototype.workspace_init_loop import (
    run_workspace_bootstrap_loop,
)

# No inner tick / no schedule due: short poll so the loop can print async tool_bg output
# without blocking on readline indefinitely.
_REPL_IDLE_POLL_SEC = 0.1


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


def _process_due_schedule_events(
    ws: Path,
    *,
    run_turn_sync: Callable[[str], str],
) -> None:
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


def _next_idle_wait_seconds(
    *,
    ws: Path,
    inner_tick: bool,
    last_inner_fire_mono: float | None,
) -> float:
    waits: list[float] = []
    if inner_tick:
        waits.append(
            next_inner_tick_wait_seconds(
                ws, last_inner_fire_monotonic=last_inner_fire_mono
            )
        )
    due_wait = next_due_wait_seconds(ws)
    if due_wait is not None:
        waits.append(due_wait)
    if not waits:
        return 1.0
    return min(waits)


def _next_due_wait_seconds_only(ws: Path) -> float | None:
    return next_due_wait_seconds(ws)


def _posix_stdin_drain_nonblock(fd: int) -> bytes:
    if fcntl is None:
        raise RuntimeError("fcntl is required for POSIX REPL stdin pump")
    acc = bytearray()
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    try:
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        while True:
            try:
                chunk = os.read(fd, 65536)
            except BlockingIOError:
                break
            except InterruptedError:
                continue
            if not chunk:
                break
            acc.extend(chunk)
    finally:
        fcntl.fcntl(fd, fcntl.F_SETFL, flags)
    return bytes(acc)


# Partial stdin without a line end can otherwise block inner tick forever (IME / escape bytes).
_STDIN_PARTIAL_STALE_SEC = 2.5


def _stdin_buffer_has_complete_line(buf: bytearray) -> bool:
    return b"\n" in buf or b"\r" in buf


def _pop_line_from_stdin_buffer(buf: bytearray) -> str | None:
    if not buf:
        return None
    try:
        nl_at = buf.index(b"\n")
        raw = bytes(buf[:nl_at])
        del buf[: nl_at + 1]
        return raw.decode("utf-8", errors="replace").rstrip("\r")
    except ValueError:
        pass
    try:
        cr_at = buf.index(b"\r")
        raw = bytes(buf[:cr_at])
        end = cr_at + 1
        if end < len(buf) and buf[end] == 0x0A:
            end += 1
        del buf[:end]
        return raw.decode("utf-8", errors="replace")
    except ValueError:
        return None


def _append_repl_presence_transcript(ws: Path, kind: PresenceSignal) -> None:
    paths = WorkspacePaths(root=ws.resolve())
    content = (
        REPL_PRESENCE_USER_TEXT_ONLINE
        if kind == "repl_online"
        else REPL_PRESENCE_USER_TEXT_OFFLINE
    )
    append_jsonl_with_db(
        paths.transcript,
        {
            "role": "user",
            "content": content,
            "ts": utc_iso_ts(),
            "uuid": str(uuid.uuid4()),
            "presence": kind,
        },
    )


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


_REPL_INNER_TICK_ENV_KEYS = (
    "INTY_V2_PROTO_INNER_TICK_ENABLED",
    "INTY_V2_PROTO_INNER_TICK_SEC",
    "INTY_V2_PROTO_INNER_TICK_MIN_GAP_SEC",
    "INTY_V2_PROTO_INNER_TICK_MIN_TRANSCRIPT_MSGS",
    "INTY_V2_PROTO_AI_PRIVATE_MAX_CHARS",
)


def _log_repl_inner_tick_env(ws: Path) -> None:
    """REPL 启动后写入日志，便于对照 `.env` 与进程内 `os.environ`（dotenv 在 main 导入时已加载）。"""
    pairs = " ".join(f"{k}={os.environ.get(k)!r}" for k in _REPL_INNER_TICK_ENV_KEYS)
    logger.info(
        "repl startup inner_tick env cwd={} workspace={} {}",
        os.getcwd(),
        ws.resolve(),
        pairs,
    )
    tick_on = inner_tick_enabled_from_env()
    wait_s = next_inner_tick_wait_seconds(
        ws, last_inner_fire_monotonic=time.monotonic()
    )
    logger.info(
        "repl startup inner_tick effective enabled={} next_inner_tick_wait_sec={:.1f} "
        "(transcript before this session repl_online/online_ack)",
        tick_on,
        wait_s,
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
    再回到「等 stdin / 空闲（含内在节拍）」。若返回 False，REPL 应退出。

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
                logger.warning(
                    "repl turn recovered from invalid OpenRouter JSON: {}", exc
                )
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
            inner_tick_turn=False,
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


def _consume_pending_after_inner_tick(
    pending: queue.Queue[tuple[str, bool] | None],
    *,
    drain_user_lines: Callable[[str, bool], bool],
) -> bool:
    """内在节拍回合结束后：若队列里已有用户行则继续回复。返回 False 表示应结束 REPL。"""
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
    inner_tick_turn: bool,
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
                    inner_tick_turn=inner_tick_turn,
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
    # Do not print async output while the user may be mid-line in the TTY line discipline
    # (interleaved stdout corrupts backspace). We still drain the tool_bg queue on each
    # select timeout so long chat waits can show async-tool lines without a newline.
    # Inner tick runs a sync tool loop: suppress async-tool stdout during this turn so the
    # user sees no interleaved replies until the turn finishes (outer loop then drains).
    while not done.is_set():
        r, _, _ = select.select([stdin_fd], [], [], 0.1)
        if not r:
            if not inner_tick_turn:
                _drain_async_tool_events(ws)
            continue
        raw = sys.stdin.readline()
        if not inner_tick_turn:
            _drain_async_tool_events(ws)
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
    if not inner_tick_turn:
        _drain_async_tool_events(ws)
    if exc:
        raise exc[0]
    return result["out"]


def _repl_interactive_loop_posix(
    ws: Path,
    *,
    debug_print_system: bool,
    inner_tick: bool,
) -> None:
    pending: queue.Queue[tuple[str, bool] | None] = queue.Queue()
    stdin_fd = sys.stdin.fileno()
    stdin_byte_buf = bytearray()
    stdin_partial_since: float | None = None
    last_inner_fire_mono: float | None = (
        time.monotonic() if inner_tick else None
    )
    print("> ", end="", flush=True)

    while True:
        _drain_async_tool_events(ws)
        _process_due_schedule_events(
            ws,
            run_turn_sync=lambda text: _run_turn_with_stdin_pump(
                ws,
                pending,
                user_text=text,
                inner_tick_turn=False,
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
            if not _posix_run_user_turn_and_drain_queue(
                ws,
                pending,
                line,
                debug_print_system=debug_print_system,
                first_line_already_echoed=echoed,
            ):
                break
            continue

        if inner_tick:
            wait = _next_idle_wait_seconds(
                ws=ws,
                inner_tick=True,
                last_inner_fire_mono=last_inner_fire_mono,
            )
            if wait <= 0.0:
                if stdin_byte_buf and not _stdin_buffer_has_complete_line(
                    stdin_byte_buf
                ):
                    now_m = time.monotonic()
                    if stdin_partial_since is None:
                        stdin_partial_since = now_m
                    if now_m - stdin_partial_since >= _STDIN_PARTIAL_STALE_SEC:
                        logger.debug(
                            "repl stdin drop stale partial stdin_bytes={}",
                            len(stdin_byte_buf),
                        )
                        stdin_byte_buf.clear()
                        stdin_partial_since = None
                    else:
                        r_p, _, _ = select.select([stdin_fd], [], [], 0.1)
                        if r_p:
                            try:
                                stdin_byte_buf.extend(
                                    _posix_stdin_drain_nonblock(stdin_fd)
                                )
                            except KeyboardInterrupt:
                                print()
                                break
                            if _stdin_buffer_has_complete_line(stdin_byte_buf):
                                stdin_partial_since = None
                        continue
                tick_remain = next_inner_tick_wait_seconds(
                    ws, last_inner_fire_monotonic=last_inner_fire_mono
                )
                if tick_remain > 0.0:
                    continue
                logger.debug("repl inner_tick branch=fire wait_s={:.1f}", wait)
                t0 = time.perf_counter()
                out = _run_turn_with_stdin_pump(
                    ws,
                    pending,
                    user_text="",
                    inner_tick_turn=True,
                    debug_print_system=debug_print_system,
                )
                last_inner_fire_mono = time.monotonic()
                _print_assistant_reply(out, time.perf_counter() - t0)
                print("> ", end="", flush=True)
                if not _consume_pending_after_inner_tick(
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
                max_seconds=REPL_IDLE_MAX_SLEEP_CHUNK_SEC,
            )
            if stdin_byte_buf:
                sleep_s = min(sleep_s, 0.15)
            r, _, _ = select.select([stdin_fd], [], [], sleep_s)
            if not r:
                continue
            try:
                new_b = _posix_stdin_drain_nonblock(stdin_fd)
            except KeyboardInterrupt:
                print()
                break
            if new_b == b"":
                print()
                break
            stdin_byte_buf.extend(new_b)
            if not _stdin_buffer_has_complete_line(stdin_byte_buf):
                if stdin_partial_since is None:
                    stdin_partial_since = time.monotonic()
                continue
            stdin_partial_since = None
            line = _pop_line_from_stdin_buffer(stdin_byte_buf)
            if line is None:
                continue
        else:
            due_wait = _next_due_wait_seconds_only(ws)
            if due_wait is None:
                r, _, _ = select.select(
                    [stdin_fd], [], [], _REPL_IDLE_POLL_SEC
                )
                if not r:
                    continue
                try:
                    raw = sys.stdin.readline()
                except KeyboardInterrupt:
                    print()
                    break
                if raw == "":
                    print()
                    break
                line = raw.rstrip("\r\n")
            else:
                sleep_s = clamp_sleep_seconds(
                    due_wait,
                    min_seconds=0.05,
                    max_seconds=REPL_IDLE_MAX_SLEEP_CHUNK_SEC,
                )
                r, _, _ = select.select([stdin_fd], [], [], sleep_s)
                if not r:
                    continue
                try:
                    raw = sys.stdin.readline()
                except KeyboardInterrupt:
                    print()
                    break
                if raw == "":
                    print()
                    break
                line = raw.rstrip("\r\n")

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
    inner_tick: bool,
) -> None:
    """Windows / 非 TTY：沿用守护线程读 stdin（无法在主线程 select）。"""
    line_queue, _ = spawn_stdin_line_reader()
    last_inner_fire_mono: float | None = (
        time.monotonic() if inner_tick else None
    )
    print("> ", end="", flush=True)

    while True:
        _drain_async_tool_events(ws)
        _process_due_schedule_events(
            ws,
            run_turn_sync=lambda text: asyncio.run(
                run_turn(
                    ws,
                    text,
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
            if not _daemon_run_user_turn_and_drain_queue(
                ws,
                line_queue,
                line,
                debug_print_system=debug_print_system,
                first_line_already_echoed=echoed,
            ):
                break
            continue

        if inner_tick:
            wait = _next_idle_wait_seconds(
                ws=ws,
                inner_tick=True,
                last_inner_fire_mono=last_inner_fire_mono,
            )
            if wait <= 0.0:
                tick_remain = next_inner_tick_wait_seconds(
                    ws, last_inner_fire_monotonic=last_inner_fire_mono
                )
                if tick_remain > 0.0:
                    continue
                logger.debug("repl inner_tick branch=fire wait_s={:.1f}", wait)
                t0 = time.perf_counter()
                print("> ", end="", flush=True)
                out = asyncio.run(
                    run_turn(
                        ws,
                        "",
                        inner_tick_turn=True,
                        debug_print_system=debug_print_system,
                        llm_trace=True,
                    )
                )
                last_inner_fire_mono = time.monotonic()
                _print_assistant_reply(out, time.perf_counter() - t0)
                print("> ", end="", flush=True)
                if not _consume_pending_after_inner_tick(
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
                max_seconds=REPL_IDLE_MAX_SLEEP_CHUNK_SEC,
            )
            try:
                item = line_queue.get(timeout=sleep_s)
            except queue.Empty:
                continue
        else:
            due_wait = _next_due_wait_seconds_only(ws)
            if due_wait is None:
                try:
                    item = line_queue.get(timeout=_REPL_IDLE_POLL_SEC)
                except queue.Empty:
                    continue
            else:
                sleep_s = clamp_sleep_seconds(
                    due_wait,
                    min_seconds=0.05,
                    max_seconds=REPL_IDLE_MAX_SLEEP_CHUNK_SEC,
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
        if not _daemon_run_user_turn_and_drain_queue(
            ws,
            line_queue,
            line,
            debug_print_system=debug_print_system,
            first_line_already_echoed=echoed,
        ):
            break


def _repl_interactive_loop(
    ws: Path,
    *,
    debug_print_system: bool,
    inner_tick: bool,
) -> None:
    """
    长耗时 turn（如生图）期间仍可读入下一行：在 TTY + POSIX 上由主线程 select+readline 泵入队列，
    `run_turn` 放在工作线程；否则退回守护线程读 stdin。
    """
    if _use_posix_stdin_pump():
        _repl_interactive_loop_posix(
            ws, debug_print_system=debug_print_system, inner_tick=inner_tick
        )
    else:
        _repl_interactive_loop_daemon(
            ws, debug_print_system=debug_print_system, inner_tick=inner_tick
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


_DEFAULT_BOOTSTRAP_USER_TEMPLATE = (
    "我们刚选定彼此，我还不是完全体：请你先自然问清楚我希望你以哪种 companionship 陪伴我（例如朋友、爱人、亲人或我自定义），"
    "确认后再按该关系类型把自己安顿好；跟我自然聊出称呼、你怎么称呼自己、相处上的底线；节奏随我，不必像填设置表。"
    "在你能静默完成的那部分就绪之后，请邀请我一起定义你，并自然地问我愿分享的基本信息（怎么称呼我、希望怎样被称呼等），不要像问卷。"
    "别跟我讲文件夹或配置文件名字；需要默认身份编号时用人话问一句就行。"
    "请你自己完成该完成的事，不要推给我去终端替你初始化。"
)

# repl 自动初始化时传给 agentic 循环的用户消息（不当作 REPL 输入回显）
_REPL_SILENT_INIT_USER_MESSAGE_TEMPLATE = (
    "用户刚打开对话。你是刚被选中、还没被完全记清的陪伴 AI：先自然打个招呼，并先确认用户希望的 companionship 类型（可给朋友、爱人、亲人、其他自定义作为示例）。"
    "按用户节奏聊，需要时用工具静默记下；不要对用户提工作区、文件名或清单式提问。"
    "当你内部该落盘的部分就绪后，在本轮结束前邀请用户一起定义你（称呼、你怎么称呼自己、相处底线），"
    "并自然地询问关于对方的基本信息（怎么称呼对方、希望怎样被称呼等），像聊天而不是填表。"
)

# 已初始化但 transcript 仍为空、且 IDENTITY/USER 仍像占位：启动时由助手先开口（写入 transcript）
_REPL_STARTUP_PROFILE_INQUIRY_USER_MESSAGE_TEMPLATE = (
    "（用户刚打开对话，尚未输入。）请你先开口：用陪伴语气自然发问，先确认用户希望的 companionship 类型，再继续，"
    "了解你希望自己的称呼、你怎么称呼自己、以及关于对方的基本信息（怎么称呼对方等）；"
    "不要提工作区或文件名，不要像问卷。"
)


def _default_bootstrap_user_message() -> str:
    return _DEFAULT_BOOTSTRAP_USER_TEMPLATE


def _repl_silent_init_user_message() -> str:
    return _REPL_SILENT_INIT_USER_MESSAGE_TEMPLATE


def _repl_startup_profile_inquiry_user_message() -> str:
    return _REPL_STARTUP_PROFILE_INQUIRY_USER_MESSAGE_TEMPLATE


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
) -> None:
    """交互循环，输入 quit 或 EOF 结束。"""
    ws = workspace or _default_workspace()
    try:
        _init_proto_logging(ws, log_file, no_log_file)
        _configure_llm_trace_for_workspace(ws)
        _log_repl_inner_tick_env(ws)
        start_schedule_scheduler(ws)
        logger.debug("cli repl start ws={}", ws.resolve())
        if not is_workspace_initialized(ws):
            logger.debug(
                "repl startup branch=bootstrap_auto_init (workspace not initialized)"
            )
            t0 = time.perf_counter()
            try:
                out = run_workspace_bootstrap_loop(
                    ws,
                    _repl_silent_init_user_message(),
                    llm_trace=True,
                )
            except OpenRouterInvalidJsonError as exc:
                logger.warning(
                    "repl startup bootstrap recovered from invalid OpenRouter JSON: {}",
                    exc,
                )
                _print_openrouter_invalid_json_retry_hint()
                return
            _print_assistant_reply(out, time.perf_counter() - t0)
        elif needs_startup_profile_inquiry(ws):
            logger.debug(
                "repl startup branch=startup_profile_inquiry (empty transcript, stub profile)"
            )
            t0 = time.perf_counter()
            try:
                out = asyncio.run(
                    run_turn(
                        ws,
                        _repl_startup_profile_inquiry_user_message(),
                        debug_print_system=debug_print_system,
                        llm_trace=True,
                    )
                )
            except OpenRouterInvalidJsonError as exc:
                logger.warning(
                    "repl startup profile inquiry recovered from invalid OpenRouter JSON: {}",
                    exc,
                )
                _print_openrouter_invalid_json_retry_hint()
                return
            _print_assistant_reply(out, time.perf_counter() - t0)
        else:
            logger.debug("repl startup branch=interactive (ready for user input)")
        tick_on = inner_tick_enabled_from_env()
        logger.debug("repl interactive inner_tick_enabled={}", tick_on)
        repl_presence_tracked = False
        if is_workspace_initialized(ws):
            _append_repl_presence_transcript(ws, "repl_online")
            repl_presence_tracked = True
            try:
                t0_ack = time.perf_counter()
                out_ack = asyncio.run(
                    run_turn(
                        ws,
                        REPL_ONLINE_ACK_USER_TEXT,
                        debug_print_system=debug_print_system,
                        llm_trace=True,
                        repl_online_ack_turn=True,
                    )
                )
                _print_assistant_reply(out_ack, time.perf_counter() - t0_ack)
            except OpenRouterInvalidJsonError as exc:
                logger.warning(
                    "repl online-ack turn recovered from invalid OpenRouter JSON: {}",
                    exc,
                )
                _print_openrouter_invalid_json_retry_hint()
                paths = WorkspacePaths(root=ws.resolve())
                if undo_trailing_repl_online_presence_line(paths.transcript):
                    logger.debug(
                        "repl online-ack failed: removed trailing repl_online presence line"
                    )
                repl_presence_tracked = False
                return
        try:
            _repl_interactive_loop(
                ws, debug_print_system=debug_print_system, inner_tick=tick_on
            )
        finally:
            if repl_presence_tracked:
                _append_repl_presence_transcript(ws, "repl_offline")
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
