"""Cyclopts entry: Inty backend WebSocket REPL only (no local workspace turn loop)."""

from __future__ import annotations

import codecs
import os
import sys
import time
import uuid
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Annotated, Any, Callable, Deque, Mapping

from cyclopts import App, Parameter
from loguru import logger

_PKG_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PKG_DIR.parent.parent
if __package__ is None:
    sys.path.insert(0, str(_PKG_DIR.parent))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from .backend_chat_ws import (
    BackendChatWsBridge,
    BackendChatWsError,
    default_api_base_url,
    http_base_to_ws_chat_url,
)
from .proto_log import (
    configure_proto_log,
    repl_wall_ts_str,
    resolve_proto_log_file,
)
from .repl_dotenv import load_prototype_dotenv
from .repl_message_io import format_ws_error_banner, pop_downlink_item

load_prototype_dotenv()


def _default_workspace() -> Path:
    return Path(__file__).resolve().parent / "workspace"


def _repl_transcript_id_suffix(ids: Mapping[str, str]) -> str:
    u = ids.get("user_msg_uuid", "")
    a = ids.get("assistant_msg_uuid", "")
    ls = ids.get("langsmith_trace_id", "")
    lsr = ids.get("langsmith_run_id", "")
    if not u and not a and not ls and not lsr:
        return ""
    parts: list[str] = []
    if u:
        parts.append(f"user={u}")
    if a:
        parts.append(f"asst={a}")
    if ls:
        parts.append(f"langsmith_trace_id={ls}")
    if lsr:
        parts.append(f"langsmith_run_id={lsr}")
    return " " + " ".join(parts)


def _repl_banner_suffix_ids(
    transcript_ids: Mapping[str, str] | None,
    meta_data: Mapping[str, Any] | None,
) -> dict[str, str]:
    out: dict[str, str] = {}
    if transcript_ids:
        for k in (
            "user_msg_uuid",
            "assistant_msg_uuid",
            "langsmith_trace_id",
            "langsmith_run_id",
        ):
            v = transcript_ids.get(k)
            if v:
                out[k] = str(v)
    if meta_data:
        for k in ("user_msg_uuid", "langsmith_trace_id", "langsmith_run_id"):
            raw = meta_data.get(k)
            if raw and k not in out:
                s = str(raw).strip()
                if s:
                    out[k] = s
        if "user_msg_uuid" not in out:
            ru = meta_data.get("reply_to_user_msg_uuid")
            if ru:
                s = str(ru).strip()
                if s:
                    out["user_msg_uuid"] = s
    return out


def _repl_assistant_banner_label(
    ids: Mapping[str, str] | None,
    *,
    meta_data: Mapping[str, Any] | None = None,
) -> str:
    src = None
    if meta_data:
        src = meta_data.get("source")
    if src == "tool_bg":
        return "toolcall"
    if src == "inner_tick":
        return "inner-tick"
    if src == "chat":
        return "chat"
    if ids:
        raw = ids.get("assistant_source", "chat")
        if raw == "inner_tick":
            return "inner-tick"
        if raw == "chat":
            return "chat"
    return "chat"


def _print_repl_user_input(text: str, *, message_uuid: str) -> None:
    print(f"[{repl_wall_ts_str()}] user-input message-uuid={message_uuid}")
    print(text)


def _print_assistant_reply(
    out: str,
    elapsed_s: float,
    *,
    transcript_ids: Mapping[str, str] | None = None,
    repl_source_label: str | None = None,
    meta_data: Mapping[str, Any] | None = None,
) -> None:
    ms = elapsed_s * 1000
    merged = _repl_banner_suffix_ids(transcript_ids, meta_data)
    suffix = _repl_transcript_id_suffix(merged)
    label = repl_source_label or _repl_assistant_banner_label(
        transcript_ids, meta_data=meta_data
    )
    print(f"[{repl_wall_ts_str()}] {label} {ms:.0f}ms{suffix}")
    print(out)


def _init_proto_logging(
    workspace: Path,
    log_file: Path | None,
    no_log_file: bool,
) -> None:
    resolved = resolve_proto_log_file(
        workspace, explicit=log_file, no_log_file=no_log_file
    )
    configure_proto_log(resolved)
    logger.info(
        "inty_v2 proto logging file={}",
        str(resolved) if resolved is not None else "(stderr only)",
    )


def _print_send_turn_exception(exc: BaseException) -> None:
    """Log and print a failure from ``bridge.send_turn`` / ``fut.result()``."""
    if isinstance(exc, BackendChatWsError):
        print(
            f"[{repl_wall_ts_str()}] chat-ws-error code={exc.code} "
            f"message={exc.agent_message!r}"
        )
        return
    logger.opt(exception=exc).error("backend ws turn failed")
    print(f"[{repl_wall_ts_str()}] error: {exc}")


def _resolve_chat_agent_id_cli(agent_id: str | None) -> str:
    if agent_id is not None and str(agent_id).strip():
        return str(agent_id).strip()
    env = os.environ.get("INTY_V2_CHAT_AGENT_ID", "").strip()
    if env:
        return env
    raise SystemExit(
        "repl requires --agent-id or environment INTY_V2_CHAT_AGENT_ID"
    )


def _resolve_bearer_token_cli() -> str:
    t = (
        os.environ.get("INTY_ACCESS_TOKEN", "").strip()
        or os.environ.get("INTY_BEARER_TOKEN", "").strip()
    )
    if t:
        return t
    p = _REPO_ROOT / ".inty_ops_bearer_token"
    if p.is_file():
        try:
            ft = p.read_text(encoding="utf-8").strip()
        except OSError:
            ft = ""
        if ft:
            return ft
    raise SystemExit(
        "repl needs INTY_ACCESS_TOKEN, INTY_BEARER_TOKEN, or repo-root .inty_ops_bearer_token "
        "(written by backend/ops/start.sh --local)"
    )


_BACKEND_WS_SIDEBAND_POLL_SEC = 0.25


def _posix_select_module_for_stdin() -> Any | None:
    """``select`` for TTY stdin multiplexing, or None when unsupported."""
    if sys.platform == "win32" or not sys.stdin.isatty():
        return None
    try:
        import select as select_mod  # noqa: PLC0415
    except ImportError:
        return None
    return select_mod


def _write_pipe1(wfd: int) -> None:
    try:
        os.write(wfd, b"\x00")
    except OSError:
        pass


def _duplex_inflight_degraded_wait(fut: Future) -> None:
    """No stdin multiplex: wait without queueing the next line (e.g. Windows / non-tty)."""
    while not fut.done():
        time.sleep(_BACKEND_WS_SIDEBAND_POLL_SEC)


def _duplex_inflight_posix_select_wait(
    fut: Future,
    rpipe: int,
    pending: Deque[str],
    *,
    stdin_fd: int,
    readline_fn: Callable[[], str],
    select_fn: Callable[..., tuple[list[int], list[int], list[int]]],
    poll_sec: float = _BACKEND_WS_SIDEBAND_POLL_SEC,
    prompt: str = "> ",
) -> None:
    """Block until ``fut`` is done, appending any full user lines to ``pending``; no try_pop (MVP).

    Prints ``prompt`` before the first block on stdin and after each full line if the turn is
    still in flight, so the user can type ahead with an explicit REPL line marker.
    """
    sys.stdout.write(prompt)
    sys.stdout.flush()
    while not fut.done():
        rlist, _, _ = select_fn(
            [stdin_fd, rpipe], [], [], poll_sec
        )
        for ready in rlist:
            if ready == rpipe:
                try:
                    os.read(rpipe, 256)
                except OSError:
                    pass
            elif ready == stdin_fd:
                line = readline_fn()
                if line == "":
                    raise EOFError
                pending.append(
                    line[:-1] if line.endswith("\n") else line
                )
                if not fut.done():
                    sys.stdout.write(prompt)
                    sys.stdout.flush()


def _readline_backend_ws_with_sideband(
    bridge: BackendChatWsBridge, prompt: str
) -> str:
    """Block for one user line while printing late server-pushed chat frames (POSIX TTY).

    Uses cbreak + no echo and a local buffer so a sideband assistant frame can clear the
    current input line, print the message, then redraw ``prompt`` and any partial input.
    """
    sel = _posix_select_module_for_stdin()
    if sel is None:
        return input(prompt)
    import termios  # noqa: PLC0415
    import tty  # noqa: PLC0415

    fd = sys.stdin.fileno()
    old_attr = termios.tcgetattr(fd)
    dec = codecs.getincrementaldecoder("utf-8")()
    buf = ""
    tty_ready = False
    try:
        tty.setcbreak(fd)
        attrs = termios.tcgetattr(fd)
        attrs[3] &= ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSADRAIN, attrs)
        tty_ready = True
        sys.stdout.write(prompt + buf)
        sys.stdout.flush()

        def redraw_edit_line() -> None:
            sys.stdout.write("\r\033[2K" + prompt + buf)
            sys.stdout.flush()

        def emit_sideband_item(item: Mapping[str, Any]) -> None:
            sys.stdout.write("\r\033[2K")
            sys.stdout.flush()
            print()
            if item["kind"] == "assistant":
                _print_assistant_reply(
                    item["text"],
                    0.0,
                    meta_data=item.get("meta_data") or {},
                )
            else:
                print(
                    format_ws_error_banner(
                        item["code"],
                        item["message"],
                        wall_ts=repl_wall_ts_str(),
                    )
                )
            sys.stdout.write(prompt + buf)
            sys.stdout.flush()

        while True:
            try:
                r, _, _ = sel.select(
                    [sys.stdin], [], [], _BACKEND_WS_SIDEBAND_POLL_SEC
                )
            except (ValueError, OSError):
                return input(prompt)
            if not r:
                item = pop_downlink_item(bridge)
                if item is not None:
                    emit_sideband_item(item)
                continue
            while True:
                chunk = os.read(fd, 1)
                if not chunk:
                    raise EOFError
                text = dec.decode(chunk, final=False)
                if not text:
                    continue
                for ch in text:
                    if ch in ("\r", "\n"):
                        sys.stdout.write("\r\033[2K")
                        sys.stdout.write(prompt + buf + "\n")
                        sys.stdout.flush()
                        return buf
                    if ch == "\x04":
                        if not buf:
                            raise EOFError
                        continue
                    if ch in ("\x7f", "\x08"):
                        if buf:
                            buf = buf[:-1]
                            redraw_edit_line()
                        continue
                    if ord(ch) < 32 and ch != "\t":
                        continue
                    buf += ch
                    redraw_edit_line()
                r2, _, _ = sel.select([sys.stdin], [], [], 0)
                if not r2:
                    break
    finally:
        if tty_ready:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_attr)


def _repl_interactive_backend_ws_loop(bridge: BackendChatWsBridge, agent_id: str) -> None:
    """Full-duplex REPL: ``send_turn`` on a worker thread; queue lines during inflight (POSIX TTY ``select`` + pipe).

    No ``try_pop_queued_chat`` while a turn is in flight (MVP, shared _response_q).
    """
    print(
        f"[{repl_wall_ts_str()}] backend-ws repl (agent_id={agent_id}); "
        "quit / exit / q to leave; history lives on the server. "
        "^D while waiting for a reply (POSIX TTY) disconnects without waiting for that reply."
    )
    pending: Deque[str] = deque()
    with ThreadPoolExecutor(max_workers=1) as ex:
        while True:
            if pending:
                line = pending.popleft()
            else:
                try:
                    line = _readline_backend_ws_with_sideband(bridge, "> ")
                except EOFError:
                    print()
                    break
            st = line.strip()
            if st in ("quit", "exit", "q"):
                break
            if not st:
                continue
            msg_uuid = str(uuid.uuid4())
            _print_repl_user_input(line, message_uuid=msg_uuid)
            t0 = time.perf_counter()
            fut = ex.submit(bridge.send_turn, agent_id, line, msg_uuid)
            rpipe, wpipe = os.pipe()
            err_exc: Exception | None = None
            out: str | None = None
            try:
                fut.add_done_callback(
                    lambda _done_f, wpipe_fd=wpipe: _write_pipe1(wpipe_fd)
                )
                try:
                    sel = _posix_select_module_for_stdin()
                    if sel is not None:
                        _duplex_inflight_posix_select_wait(
                            fut,
                            rpipe,
                            pending,
                            stdin_fd=sys.stdin.fileno(),
                            readline_fn=sys.stdin.readline,
                            select_fn=sel.select,
                        )
                    else:
                        _duplex_inflight_degraded_wait(fut)
                except EOFError:
                    bridge.stop()
                    print()
                    break
                try:
                    out = fut.result()
                except (
                    BackendChatWsError,
                    TimeoutError,
                    OSError,
                    RuntimeError,
                    ValueError,
                ) as e:
                    err_exc = e
            finally:
                for fd in (rpipe, wpipe):
                    try:
                        os.close(fd)
                    except OSError:
                        pass
            if err_exc is not None:
                _print_send_turn_exception(err_exc)
                continue
            assert out is not None
            reply_text, reply_meta = out
            # Line-buffered TTY delivers whole lines; blank line separates the reply from any in-flight input context.
            print()
            _print_assistant_reply(
                reply_text, time.perf_counter() - t0, meta_data=reply_meta
            )


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
    bridge = BackendChatWsBridge(ws_url=url, bearer_token=token)
    bridge.start()
    try:
        _repl_interactive_backend_ws_loop(bridge, agent_resolved)
    finally:
        bridge.stop()


app = App(
    name="inty-chat-ws-repl",
    help="Inty /api/v1/chat/ws terminal client; --workspace is for local logs only.",
)


@app.command
def repl(
    workspace: Annotated[
        Path | None,
        Parameter(
            name="--workspace",
            help="日志等本地输出目录；默认包内 workspace/",
        ),
    ] = None,
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
    """连接 Inty /api/v1/chat/ws，交互输入；对话与 bootstrap 由服务端处理。"""
    ws = workspace or _default_workspace()
    _repl_run_backend_ws_branch(
        ws,
        agent_id=agent_id,
        api_base_url=api_base_url,
        log_file=log_file,
        no_log_file=no_log_file,
    )


if __name__ == "__main__":
    app()
