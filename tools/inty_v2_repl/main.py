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
from pathlib import Path
from typing import Annotated, Callable, Mapping

from cyclopts import App, Parameter
from dotenv import load_dotenv
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

from tools.inty_v2_repl.client import load_prototype_dotenv
from tools.inty_v2_repl.client import OpenRouterInvalidJsonError
from tools.inty_v2_repl.backend_chat_ws import (
    BackendChatWsBridge,
    BackendChatWsError,
    chat_turn_single_http_base,
    default_api_base_url,
    http_base_to_ws_chat_url,
)

load_prototype_dotenv()
load_dotenv(_REPO_ROOT / ".env")

from app.core.repl_input.sleep_chunk import clamp_sleep_seconds
from app.core.repl_input.stdin_queue import spawn_stdin_line_reader

from tools.inty_v2_repl.bootstrap import (
    init_workspace as bootstrap_init_workspace,
)
from tools.inty_v2_repl.llm_trace import configure_llm_trace_file
from tools.inty_v2_repl.proto_log import (
    configure_proto_log,
    repl_wall_ts_str,
    resolve_proto_log_file,
)

from tools.inty_v2_repl.inner_tick_schedule import (
    REPL_IDLE_MAX_SLEEP_CHUNK_SEC,
    inner_tick_enabled_from_env,
    next_inner_tick_wait_seconds,
)
from tools.inty_v2_repl.orchestrator import (
    ReplTurnSuperseded,
    is_workspace_initialized,
    needs_startup_profile_inquiry,
    run_turn,
)
from tools.inty_v2_repl.tool_background import (
    pop_output_events_nowait,
)
from tools.inty_v2_repl.schedule_queue import (
    mark_task_fired,
    next_due_wait_seconds,
    mark_task_retry,
    pop_due_task_events_nowait,
    scheduled_task_synthetic_user_text,
    start_schedule_scheduler,
    stop_schedule_scheduler,
)
from tools.inty_v2_repl.memory_store_registry import (
    flush_memory_store,
    shutdown_memory_store,
)
from tools.inty_v2_repl.jsonl_db_store import (
    append_jsonl_with_db,
    flush_jsonl_db_store,
    shutdown_jsonl_db_store,
)
from tools.inty_v2_repl.models import (
    PresenceSignal,
    REPL_ONLINE_ACK_USER_TEXT,
    REPL_PRESENCE_USER_TEXT_OFFLINE,
    REPL_PRESENCE_USER_TEXT_ONLINE,
    undo_trailing_repl_online_presence_line,
)
from tools.inty_v2_repl.paths import WorkspacePaths
from tools.inty_v2_repl.utc import utc_iso_ts
from tools.inty_v2_repl.workspace_init_loop import (
    run_workspace_bootstrap_loop,
)

# No inner tick / no schedule due: short poll so the loop can print async tool_bg output
# without blocking on readline indefinitely.
_REPL_IDLE_POLL_SEC = 0.1


def _default_workspace() -> Path:
    return Path(__file__).resolve().parent / "workspace"


def _repl_transcript_id_suffix(ids: Mapping[str, str]) -> str:
    u = ids.get("user_msg_uuid", "")
    a = ids.get("assistant_msg_uuid", "")
    tr = ids.get("trace_id", "")
    if not u and not a and not tr:
        return ""
    return f" user={u} asst={a} trace={tr}"


def _repl_assistant_banner_label(ids: Mapping[str, str] | None) -> str:
    if not ids:
        return "AI-chat"
    raw = ids.get("assistant_source", "chat")
    if raw == "inner_tick":
        return "inner-tick"
    return "AI-chat"


def _print_repl_user_input(text: str) -> None:
    print(f"[{repl_wall_ts_str()}] user-input")
    print(text)


def _print_assistant_reply(
    out: str,
    elapsed_s: float,
    *,
    transcript_ids: Mapping[str, str] | None = None,
    repl_source_label: str | None = None,
) -> None:
    ms = elapsed_s * 1000
    suffix = _repl_transcript_id_suffix(transcript_ids) if transcript_ids else ""
    label = repl_source_label or _repl_assistant_banner_label(transcript_ids)
    print(f"[{repl_wall_ts_str()}] {label} {ms:.0f}ms{suffix}")
    print(out)


def _drain_async_tool_events(ws: Path) -> None:
    """Flush tool_bg 队列到 stdout。横幅 trace= 与 transcript、llm_trace(where~repl.turn.bg.*)、tool_background.jsonl 的 trace_id 对齐。勿在用户行内编辑（含 CJK 回显）期间调用。"""
    events = pop_output_events_nowait(workspace=ws)
    for ev in events:
        tr = (ev.trace_id or "").strip()
        trace_part = f" trace={tr}" if tr else ""
        print(
            f"[{repl_wall_ts_str()}] AI-tool-bg {ev.elapsed_ms}ms{trace_part} "
            f"(user={ev.user_msg_uuid[:8]} asst={ev.assistant_msg_uuid[:8]})"
        )
        print(ev.text)


def _process_due_schedule_events(
    ws: Path,
    *,
    run_turn_sync: Callable[[str], tuple[str, dict[str, str]]],
) -> None:
    events = pop_due_task_events_nowait(workspace=ws)
    for ev in events:
        synthetic_user = scheduled_task_synthetic_user_text(
            task_text=ev.task_text,
            exec_time_utc=ev.exec_time_utc,
        )
        t0 = time.perf_counter()
        try:
            out, ids = run_turn_sync(synthetic_user)
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
        id_suffix = _repl_transcript_id_suffix(ids)
        print(
            f"[{repl_wall_ts_str()}] AI-chat {int((time.perf_counter() - t0) * 1000)}ms "
            f"(schedule-task task={ev.task_id[:8]}){id_suffix}"
        )
        print(out)
        _drain_async_tool_events(ws)
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
    print(f"[{repl_wall_ts_str()}] LLM API 临时异常（上游返回非 JSON），请重试。")


def _undo_repl_online_presence_after_failed_ack(ws: Path) -> None:
    paths = WorkspacePaths(root=ws.resolve())
    if undo_trailing_repl_online_presence_line(paths.transcript):
        logger.debug(
            "repl online-ack failed: removed trailing repl_online presence line"
        )


def _print_repl_online_ack_failure_hint(exc: BaseException) -> None:
    print(f"[{repl_wall_ts_str()}] REPL 上线问候失败: {exc}")


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


def _repl_stdin_read_line_after_select() -> str | None:
    """
    在 `select` 报告 stdin 可读之后读一行。

    - TTY：优先 `import readline` 后用 `input()`，由 libedit/GNU readline 做行编辑，避免仅靠内核
      规范模式时在 Cursor 等终端里 CJK 退格与屏幕不同步。
    - 返回 `None` 表示 EOF；`""` 表示用户提交了空行（仅换行）。
    """
    try:
        is_tty = sys.stdin.isatty()
    except (OSError, ValueError):
        is_tty = False
    if is_tty:
        try:
            import readline  # noqa: F401
        except ImportError:
            raw = sys.stdin.readline()
            if raw == "":
                return None
            return raw.rstrip("\r\n")
        try:
            return input()
        except EOFError:
            return None
    raw = sys.stdin.readline()
    if raw == "":
        return None
    return raw.rstrip("\r\n")


def _repl_drain_user_turns(
    first_line: str,
    *,
    run_turn_sync: Callable[[str], tuple[str, dict[str, str]]],
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
            _drain_async_tool_events(ws)
            print("> ", end="", flush=True)
        else:
            if not cur_echoed:
                _print_repl_user_input(cur)
                logger.debug(
                    "repl interactive_turn line_chars={} preview={}",
                    len(cur),
                    _preview_line(cur),
                )
                print("> ", end="", flush=True)
            t0 = time.perf_counter()
            try:
                out, ids = run_turn_sync(cur)
            except OpenRouterInvalidJsonError as exc:
                logger.warning(
                    "repl turn recovered from invalid OpenRouter JSON: {}", exc
                )
                _print_openrouter_invalid_json_retry_hint()
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
                continue
            _print_assistant_reply(
                out,
                time.perf_counter() - t0,
                transcript_ids=ids or None,
            )
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
    def _sync(cur: str) -> tuple[str, dict[str, str]]:
        return _run_turn_with_stdin_pump(
            ws,
            pending,
            user_text=cur,
            inner_tick_turn=False,
            repl_online_ack_turn=False,
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
    def _sync(cur: str) -> tuple[str, dict[str, str]]:
        ids_out: dict[str, str] = {}
        out = asyncio.run(
            run_turn(
                ws,
                cur,
                inner_tick_turn=False,
                repl_online_ack_turn=False,
                debug_print_system=debug_print_system,
                llm_trace=True,
                repl_transcript_ids_out=ids_out,
            )
        )
        return out, ids_out

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
    repl_online_ack_turn: bool = False,
    debug_print_system: bool,
) -> tuple[str, dict[str, str]]:
    """
    `run_turn` 在工作线程里跑；主线程 select+readline。进行中时若用户又输入**非空行**，
    则协作式取消当前回合（不落盘），仅以**最后一条**非空输入重跑；空行仍入 `pending` FIFO。
    """
    cur_user = user_text
    cur_inner = inner_tick_turn
    cur_ack = repl_online_ack_turn

    while True:
        if cur_user.strip() in ("quit", "exit", "q"):
            pending.put((cur_user.strip(), True))
            return "", {}

        supersede_event = threading.Event()
        replace_slot: list[str | None] = [None]
        done = threading.Event()
        result: dict[str, object] = {}
        exc: list[BaseException] = []
        ids_out: dict[str, str] = {}

        def repl_cancel_check() -> bool:
            return supersede_event.is_set()

        def worker() -> None:
            try:
                result["out"] = asyncio.run(
                    run_turn(
                        ws,
                        cur_user,
                        inner_tick_turn=cur_inner,
                        repl_online_ack_turn=cur_ack,
                        debug_print_system=debug_print_system,
                        llm_trace=True,
                        repl_cancel_check=repl_cancel_check,
                        repl_transcript_ids_out=ids_out,
                    )
                )
                result["superseded"] = False
            except ReplTurnSuperseded:
                result["superseded"] = True
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
        while not done.is_set():
            r, _, _ = select.select([stdin_fd], [], [], 0.1)
            if not r:
                continue
            line_in = _repl_stdin_read_line_after_select()
            _drain_async_tool_events(ws)
            if line_in is None:
                pending.put(None)
            else:
                text = line_in
                if text.strip():
                    _print_repl_user_input(text)
                    logger.debug(
                        "repl stdin_pump supersede line_chars={} preview={}",
                        len(text),
                        _preview_line(text),
                    )
                    print("> ", end="", flush=True)
                    replace_slot[0] = text
                    supersede_event.set()
                else:
                    print("> ", end="", flush=True)
                    pending.put((text, True))
        t.join(timeout=3600.0)
        if exc:
            raise exc[0]
        _drain_async_tool_events(ws)
        if result.get("superseded"):
            latest = replace_slot[0]
            if latest is not None and latest.strip():
                cur_user = latest
                cur_inner = False
                cur_ack = False
            continue
        return str(result["out"]), dict(ids_out)


def _repl_interactive_loop_posix(
    ws: Path,
    *,
    debug_print_system: bool,
    inner_tick: bool,
) -> None:
    pending: queue.Queue[tuple[str, bool] | None] = queue.Queue()
    stdin_fd = sys.stdin.fileno()
    last_inner_fire_mono: float | None = time.monotonic() if inner_tick else None
    _drain_async_tool_events(ws)
    print("> ", end="", flush=True)

    while True:
        _process_due_schedule_events(
            ws,
            run_turn_sync=lambda text: _run_turn_with_stdin_pump(
                ws,
                pending,
                user_text=text,
                inner_tick_turn=False,
                repl_online_ack_turn=False,
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
                _drain_async_tool_events(ws)
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

        line: str
        got_line = False

        if inner_tick:
            wait = _next_idle_wait_seconds(
                ws=ws,
                inner_tick=True,
                last_inner_fire_mono=last_inner_fire_mono,
            )
            if wait <= 0.0:
                r0, _, _ = select.select([stdin_fd], [], [], 0.0)
                if r0:
                    try:
                        line = _repl_stdin_read_line_after_select()
                    except KeyboardInterrupt:
                        print()
                        break
                    if line is None:
                        print()
                        break
                    got_line = True
                else:
                    tick_remain = next_inner_tick_wait_seconds(
                        ws, last_inner_fire_monotonic=last_inner_fire_mono
                    )
                    if tick_remain > 0.0:
                        continue
                    logger.debug("repl inner_tick branch=fire wait_s={:.1f}", wait)
                    t0 = time.perf_counter()
                    out, ids = _run_turn_with_stdin_pump(
                        ws,
                        pending,
                        user_text="",
                        inner_tick_turn=True,
                        repl_online_ack_turn=False,
                        debug_print_system=debug_print_system,
                    )
                    last_inner_fire_mono = time.monotonic()
                    _print_assistant_reply(
                        out,
                        time.perf_counter() - t0,
                        transcript_ids=ids or None,
                    )
                    _drain_async_tool_events(ws)
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
            else:
                sleep_s = clamp_sleep_seconds(
                    wait,
                    min_seconds=0.05,
                    max_seconds=REPL_IDLE_MAX_SLEEP_CHUNK_SEC,
                )
                r, _, _ = select.select([stdin_fd], [], [], sleep_s)
                if not r:
                    continue
                try:
                    line = _repl_stdin_read_line_after_select()
                except KeyboardInterrupt:
                    print()
                    break
                if line is None:
                    print()
                    break
                got_line = True
        else:
            due_wait = _next_due_wait_seconds_only(ws)
            if due_wait is None:
                r, _, _ = select.select([stdin_fd], [], [], _REPL_IDLE_POLL_SEC)
                if not r:
                    continue
                try:
                    line = _repl_stdin_read_line_after_select()
                except KeyboardInterrupt:
                    print()
                    break
                if line is None:
                    print()
                    break
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
                    line = _repl_stdin_read_line_after_select()
                except KeyboardInterrupt:
                    print()
                    break
                if line is None:
                    print()
                    break
            got_line = True

        if not got_line:
            continue

        if line.strip() in ("quit", "exit", "q"):
            break
        if not line.strip():
            _drain_async_tool_events(ws)
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
    last_inner_fire_mono: float | None = time.monotonic() if inner_tick else None

    def _schedule_run_turn(text: str) -> tuple[str, dict[str, str]]:
        ids_out: dict[str, str] = {}
        out = asyncio.run(
            run_turn(
                ws,
                text,
                inner_tick_turn=False,
                repl_online_ack_turn=False,
                debug_print_system=debug_print_system,
                llm_trace=True,
                repl_transcript_ids_out=ids_out,
            )
        )
        return out, ids_out

    _drain_async_tool_events(ws)
    print("> ", end="", flush=True)

    while True:
        _process_due_schedule_events(ws, run_turn_sync=_schedule_run_turn)
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
                _drain_async_tool_events(ws)
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
                ids_tick: dict[str, str] = {}
                out = asyncio.run(
                    run_turn(
                        ws,
                        "",
                        inner_tick_turn=True,
                        repl_online_ack_turn=False,
                        debug_print_system=debug_print_system,
                        llm_trace=True,
                        repl_transcript_ids_out=ids_tick,
                    )
                )
                last_inner_fire_mono = time.monotonic()
                _print_assistant_reply(
                    out,
                    time.perf_counter() - t0,
                    transcript_ids=ids_tick or None,
                )
                _drain_async_tool_events(ws)
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
            _drain_async_tool_events(ws)
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


def _backend_ws_enabled(cli_flag: bool) -> bool:
    if cli_flag:
        return True
    v = os.environ.get("INTY_V2_REPL_BACKEND_WS", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _resolve_chat_agent_id_cli(agent_id: str | None) -> str:
    if agent_id is not None and str(agent_id).strip():
        return str(agent_id).strip()
    env = os.environ.get("INTY_V2_CHAT_AGENT_ID", "").strip()
    if env:
        return env
    raise SystemExit(
        "backend WebSocket mode requires --agent-id or environment INTY_V2_CHAT_AGENT_ID"
    )


def _resolve_bearer_token_cli() -> str:
    t = os.environ.get("INTY_ACCESS_TOKEN", "").strip()
    if t:
        return t
    raise SystemExit(
        "backend WebSocket mode requires INTY_ACCESS_TOKEN (Bearer JWT for the backend)"
    )


def _repl_interactive_backend_ws_loop(bridge: BackendChatWsBridge, agent_id: str) -> None:
    print(
        f"[{repl_wall_ts_str()}] backend-ws repl (agent_id={agent_id}); "
        "quit / exit / q to leave; history lives on the server."
    )
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
        _print_repl_user_input(line)
        t0 = time.perf_counter()
        try:
            out = bridge.send_turn(agent_id, line)
        except BackendChatWsError as exc:
            print(
                f"[{repl_wall_ts_str()}] chat-ws-error code={exc.code} "
                f"message={exc.agent_message!r}"
            )
            continue
        except Exception as exc:
            logger.exception("backend ws turn failed")
            print(f"[{repl_wall_ts_str()}] error: {exc}")
            continue
        _print_assistant_reply(out, time.perf_counter() - t0)


def _repl_run_backend_ws_branch(
    ws: Path,
    *,
    agent_id: str | None,
    api_base_url: str | None,
    log_file: Path | None,
    no_log_file: bool,
) -> None:
    agent_resolved = _resolve_chat_agent_id_cli(agent_id)
    base = (api_base_url or default_api_base_url()).strip()
    token = _resolve_bearer_token_cli()
    url = http_base_to_ws_chat_url(base, agent_id=agent_resolved)
    logger.info(
        "repl backend-ws api_base={} ws_url={} agent_id={}",
        base,
        url,
        agent_resolved,
    )
    _init_proto_logging(ws, log_file, no_log_file)
    _configure_llm_trace_for_workspace(ws)
    bridge = BackendChatWsBridge(ws_url=url, bearer_token=token)
    bridge.start()
    try:
        kick = bridge.drain_proactive_assistant_if_any(timeout_sec=8.0)
        if kick:
            _print_assistant_reply(kick, 0.0)
        _repl_interactive_backend_ws_loop(bridge, agent_resolved)
    finally:
        bridge.stop()
        _flush_and_shutdown_memory_store(ws.resolve())


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
    """Agentic 工具循环：按 templates/BOOTSTRAP.md 用 LLM + 文件工具初始化工作区。"""
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
    backend_ws: Annotated[
        bool,
        Parameter(
            name="--backend-ws",
            help="走本地 Inty 后端 WebSocket /api/v1/chat/ws（需 INTY_ACCESS_TOKEN 与 agent id）",
        ),
    ] = False,
    agent_id: Annotated[
        str | None,
        Parameter(
            name="--agent-id",
            help="后端聊天 agent id；可改用环境变量 INTY_V2_CHAT_AGENT_ID",
        ),
    ] = None,
    api_base_url: Annotated[
        str | None,
        Parameter(
            name="--api-base-url",
            help="HTTP API 根（默认 INTY_API_BASE_URL 或 http://127.0.0.1:8000），用于推导 ws URL",
        ),
    ] = None,
) -> None:
    """交互循环，输入 quit 或 EOF 结束。"""
    ws = workspace or _default_workspace()
    if _backend_ws_enabled(backend_ws):
        _repl_run_backend_ws_branch(
            ws,
            agent_id=agent_id,
            api_base_url=api_base_url,
            log_file=log_file,
            no_log_file=no_log_file,
        )
        return
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
                _ids_prof: dict[str, str] = {}
                out = asyncio.run(
                    run_turn(
                        ws,
                        _repl_startup_profile_inquiry_user_message(),
                        inner_tick_turn=False,
                        repl_online_ack_turn=False,
                        debug_print_system=debug_print_system,
                        llm_trace=True,
                        repl_transcript_ids_out=_ids_prof,
                    )
                )
            except OpenRouterInvalidJsonError as exc:
                logger.warning(
                    "repl startup profile inquiry recovered from invalid OpenRouter JSON: {}",
                    exc,
                )
                _print_openrouter_invalid_json_retry_hint()
                return
            _print_assistant_reply(
                out,
                time.perf_counter() - t0,
                transcript_ids=_ids_prof or None,
            )
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
                _ids_ack: dict[str, str] = {}
                out_ack = asyncio.run(
                    run_turn(
                        ws,
                        REPL_ONLINE_ACK_USER_TEXT,
                        inner_tick_turn=False,
                        repl_online_ack_turn=True,
                        debug_print_system=debug_print_system,
                        llm_trace=True,
                        repl_transcript_ids_out=_ids_ack,
                    )
                )
                _print_assistant_reply(
                    out_ack,
                    time.perf_counter() - t0_ack,
                    transcript_ids=_ids_ack or None,
                )
            except OpenRouterInvalidJsonError as exc:
                logger.warning(
                    "repl online-ack turn recovered from invalid OpenRouter JSON: {}",
                    exc,
                )
                _print_openrouter_invalid_json_retry_hint()
                _undo_repl_online_presence_after_failed_ack(ws)
                repl_presence_tracked = False
                return
            except Exception as exc:
                logger.error("repl online-ack turn failed: {}", exc)
                _print_repl_online_ack_failure_hint(exc)
                _undo_repl_online_presence_after_failed_ack(ws)
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
    backend_ws: Annotated[
        bool,
        Parameter(
            name="--backend-ws",
            help="走本地 Inty 后端 WebSocket /api/v1/chat/ws（需 INTY_ACCESS_TOKEN 与 agent id）",
        ),
    ] = False,
    agent_id: Annotated[
        str | None,
        Parameter(
            name="--agent-id",
            help="后端聊天 agent id；可改用环境变量 INTY_V2_CHAT_AGENT_ID",
        ),
    ] = None,
    api_base_url: Annotated[
        str | None,
        Parameter(
            name="--api-base-url",
            help="HTTP API 根（默认 INTY_API_BASE_URL 或 http://127.0.0.1:8000），用于推导 ws URL",
        ),
    ] = None,
) -> None:
    """单轮对话。"""
    ws = workspace or _default_workspace()
    try:
        _init_proto_logging(ws, log_file, no_log_file)
        _configure_llm_trace_for_workspace(ws)
        if _backend_ws_enabled(backend_ws):
            token = _resolve_bearer_token_cli()
            base = (api_base_url or default_api_base_url()).strip()
            aid = _resolve_chat_agent_id_cli(agent_id)
            logger.debug(
                "cli once backend-ws ws={} base={} agent_id={} message_chars={} preview={}",
                ws.resolve(),
                base,
                aid,
                len(message),
                _preview_line(message, max_len=240),
            )
            t0 = time.perf_counter()
            out = asyncio.run(
                chat_turn_single_http_base(
                    http_base=base,
                    bearer_token=token,
                    agent_id=aid,
                    user_text=message,
                )
            )
            _print_assistant_reply(out, time.perf_counter() - t0)
            return
        logger.debug(
            "cli once ws={} message_chars={} preview={}",
            ws.resolve(),
            len(message),
            _preview_line(message, max_len=240),
        )
        t0 = time.perf_counter()
        _ids_once: dict[str, str] = {}
        out = asyncio.run(
            run_turn(
                ws,
                message,
                inner_tick_turn=False,
                repl_online_ack_turn=False,
                debug_print_system=debug_print_system,
                defer_memory_update=False,
                llm_trace=True,
                repl_transcript_ids_out=_ids_once,
            )
        )
        _print_assistant_reply(
            out,
            time.perf_counter() - t0,
            transcript_ids=_ids_once or None,
        )
    finally:
        _flush_and_shutdown_memory_store(ws.resolve())


if __name__ == "__main__":
    app()
