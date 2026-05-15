"""Terminal companion for partners who ship the product: hold a real conversation against a
running Inty backend on the same WebSocket chat path as production clients; latency, reconnects,
implicit greeting, and follow-up frames all originate in the server harness, not a second brain
simulated inside this process.

Use it when you want the subjective feel of the companion under load or flaky networks; when you
need exact wire semantics or field meanings, read the package README and ``AGENTS.md`` instead of
treating this TTY as a specification surface. Cyclopts ``--help`` summarizes the assistant
**metadata section** and post-body banner lines; LangSmith URL resolution is documented there.
"""

from __future__ import annotations

import codecs
import os
import queue
import sys
import time
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Annotated, Any, Mapping

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
from .proto_log import configure_proto_log, repl_wall_ts_str
from .repl_dotenv import load_prototype_dotenv
from .repl_message_io import format_ws_error_banner, pop_downlink_item

load_prototype_dotenv()

_repl_langsmith_client: Any | None = None
_repl_langsmith_client_import_failed = False


def _repl_langsmith_url_stitched(run_uuid: str) -> str:
    """Build LangSmith UI URL from run/trace UUID when org + project (session) UUIDs are in env.

    Uses ``LANGCHAIN_WORKSPACE_ID`` / ``LANGSMITH_WORKSPACE_ID`` and
    ``LANGSMITH_PROJECT_ID`` / ``LANGCHAIN_PROJECT_ID`` (Tracer session id, not project name).
    """
    ru = (run_uuid or "").strip()
    if not ru:
        return ""
    ws = (
        os.environ.get("LANGCHAIN_WORKSPACE_ID", "").strip()
        or os.environ.get("LANGSMITH_WORKSPACE_ID", "").strip()
    )
    proj = (
        os.environ.get("LANGSMITH_PROJECT_ID", "").strip()
        or os.environ.get("LANGCHAIN_PROJECT_ID", "").strip()
    )
    if not ws or not proj:
        return ""
    try:
        from langsmith.utils import get_api_url, get_host_url

        web = get_host_url(None, get_api_url(None)).rstrip("/")
    except Exception:
        web = "https://smith.langchain.com"
    return f"{web}/o/{ws}/projects/p/{proj}/r/{ru}"


def _repl_langsmith_client_lazy() -> Any | None:
    """Single process-wide ``langsmith.Client`` for metadata-section URL resolution, or None."""
    global _repl_langsmith_client, _repl_langsmith_client_import_failed
    if _repl_langsmith_client_import_failed:
        return None
    if _repl_langsmith_client is None:
        try:
            from langsmith import Client

            _repl_langsmith_client = Client(auto_batch_tracing=False)
        except ImportError:
            _repl_langsmith_client_import_failed = True
            return None
    return _repl_langsmith_client


def _repl_langsmith_resolve_open_url(run_uuid: str) -> str:
    """LangSmith run/trace page URL for ``run_uuid`` (SDK first, then stitched env fallback)."""
    ru = (run_uuid or "").strip()
    if not ru:
        return ""
    c = _repl_langsmith_client_lazy()
    if c is not None:
        try:
            return c.get_run_url(run=SimpleNamespace(id=ru))
        except Exception:
            pass
    return _repl_langsmith_url_stitched(ru)


def _repl_metadata_correlation_tokens(ids: Mapping[str, str]) -> str:
    u = ids.get("user_msg_uuid", "")
    a = ids.get("assistant_msg_uuid", "")
    ls = ids.get("langsmith_trace_id", "")
    lsr = ids.get("langsmith_run_id", "")
    if not u and not a and not ls and not lsr:
        return ""
    parts: list[str] = []
    if u:
        parts.append(f"user_msg_uuid={u}")
    if a:
        parts.append(f"asst={a}")
    if ls:
        parts.append(f"langsmith_trace_id={ls}")
    if lsr:
        parts.append(f"langsmith_run_id={lsr}")
    return " " + " ".join(parts)


def _repl_assistant_metadata_section_suffix(
    merged: Mapping[str, str],
    meta_data: Mapping[str, Any] | None,
) -> str:
    """Space-prefixed tail of the assistant **metadata section** (correlation ids, URLs, flags)."""
    out = _repl_metadata_correlation_tokens(merged)
    tid = merged.get("langsmith_trace_id", "").strip()
    rid = merged.get("langsmith_run_id", "").strip()
    trace_url = ""
    if tid:
        trace_url = _repl_langsmith_resolve_open_url(tid)
        if trace_url:
            out += f" langsmith_trace_url={trace_url}"
    if rid and rid != tid:
        run_url = _repl_langsmith_resolve_open_url(rid)
        if run_url and run_url != trace_url:
            out += f" langsmith_run_url={run_url}"
    return out + _repl_metadata_section_flags_fragment(meta_data)


def _repl_metadata_section_flags_fragment(meta_data: Mapping[str, Any] | None) -> str:
    """Trailing metadata-section tokens from assistant ``meta_data`` flags (API snake_case)."""
    if not meta_data:
        return ""
    if meta_data.get("tool_background_started") is True:
        return " tool_background_started=true"
    return ""


def _repl_banner_suffix_ids(
    transcript_ids: Mapping[str, str] | None,
    meta_data: Mapping[str, Any] | None,
) -> dict[str, str]:
    """Merge transcript and ``meta_data`` correlation keys for the metadata section."""
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
        for k in (
            "user_msg_uuid",
            "assistant_msg_uuid",
            "langsmith_trace_id",
            "langsmith_run_id",
        ):
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


def _repl_inner_tick_activity_display(activity: str) -> str:
    """WS ``meta_data.inner_tick_activity`` uses enum values; REPL shows proactive-chat hyphenated."""
    s = (activity or "").strip()
    if s == "proactive_chat":
        return "proactive-chat"
    return s


# TODO(ux): Prefer meta_data.source == tool_bg (e.g. label "toolcall") before inner_tick_activity so
# maintenance tool_bg frames are not misread as foreground inner-tick lines.
def _repl_assistant_banner_label(
    ids: Mapping[str, str] | None,
    *,
    meta_data: Mapping[str, Any] | None = None,
) -> str:
    if meta_data and meta_data.get("companion_scheduled_reminder") is True:
        return "inner-tick scheduled-reminder"
    act_raw = None
    if meta_data:
        raw = meta_data.get("inner_tick_activity")
        if raw:
            act_raw = str(raw).strip()
    if act_raw:
        return f"inner-tick {_repl_inner_tick_activity_display(act_raw)}"
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
    """Print assistant body text, preceded by one **metadata section** line (see module docstring)."""
    ms = elapsed_s * 1000
    merged = _repl_banner_suffix_ids(transcript_ids, meta_data)
    suffix = _repl_assistant_metadata_section_suffix(merged, meta_data)
    label = repl_source_label or _repl_assistant_banner_label(
        transcript_ids, meta_data=meta_data
    )
    print(f"[{repl_wall_ts_str()}] {label} {ms:.0f}ms{suffix}")
    print(out)


def _init_proto_logging() -> None:
    configure_proto_log()
    logger.info("inty_v2 proto logging (stderr)")


def _format_cli_exc(exc: BaseException) -> str:
    if isinstance(exc, TimeoutError) and str(exc) == "":
        return repr(exc)
    return str(exc)


def _print_send_turn_exception(exc: BaseException) -> None:
    """Log and print a failure from ``bridge.post_turn`` / ``fut.result()``."""
    if isinstance(exc, BackendChatWsError):
        print(
            f"[{repl_wall_ts_str()}] chat-ws-error code={exc.code} "
            f"message={exc.agent_message!r}"
        )
        return
    logger.opt(exception=exc).error("backend ws turn failed")
    print(f"[{repl_wall_ts_str()}] error: {_format_cli_exc(exc)}")


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


def _correlation_uuid_from_meta(meta_data: Mapping[str, Any]) -> str | None:
    for k in ("user_msg_uuid", "reply_to_user_msg_uuid"):
        raw = meta_data.get(k)
        if raw:
            s = str(raw).strip()
            if s:
                return s
    return None


# TODO(ux): Server-pushed frames (inner-tick, tool_bg) use user_msg_uuid not present in outbound_t0;
# show wall-clock delta or "n/a" instead of misleading 0ms.
def _elapsed_for_downlink_assistant(
    meta_data: Mapping[str, Any],
    outbound_t0: dict[str, float],
) -> float:
    uid = _correlation_uuid_from_meta(meta_data)
    if not uid:
        return 0.0
    t0 = outbound_t0.pop(uid, None)
    if t0 is None:
        return 0.0
    return max(0.0, time.perf_counter() - t0)


def _print_tool_bg_local_image_paths_banner(meta: Mapping[str, Any]) -> None:
    """Emit one ``local-path: /abs/...`` line per server-side image path for REPL copy."""
    raw = meta.get("tool_bg_local_image_paths")
    if not isinstance(raw, list) or not raw:
        return
    for p in raw:
        if not isinstance(p, str):
            continue
        s = p.strip()
        if not s:
            continue
        print(f"local-path: {s}")


def _print_generated_image_meta_banner(meta: Mapping[str, Any]) -> None:
    """Emit ``image-url:`` for ``meta_data.generated_image`` (``gs://``, ``https://``, or local ``file://`` with fake GCS)."""
    gi = meta.get("generated_image")
    if not isinstance(gi, dict):
        return
    url = gi.get("image_url")
    if not isinstance(url, str):
        return
    s = url.strip()
    if not s:
        return
    print(f"image-url: {s}")


def _print_transcript_compaction_banner(meta: Mapping[str, Any]) -> None:
    """Emit one line when server applied transcript window compaction for this turn."""
    raw = meta.get("transcript_compaction")
    if not isinstance(raw, dict):
        return
    if not raw.get("did_compact"):
        return
    reason = raw.get("reason", "")
    before = raw.get("approx_chars_before", "")
    after = raw.get("approx_chars_after", "")
    cc = raw.get("compaction_count", "")
    print(
        f"transcript-compaction: reason={reason!r} chars_before={before} "
        f"chars_after={after} compaction_count={cc}"
    )


def _emit_downlink_item(
    item: Mapping[str, Any],
    outbound_t0: dict[str, float],
) -> None:
    if item["kind"] == "assistant":
        meta = item.get("meta_data") or {}
        elapsed = _elapsed_for_downlink_assistant(meta, outbound_t0)
        _print_assistant_reply(
            item["text"],
            elapsed,
            meta_data=meta,
        )
        _print_tool_bg_local_image_paths_banner(meta)
        _print_generated_image_meta_banner(meta)
        _print_transcript_compaction_banner(meta)
    else:
        print(
            format_ws_error_banner(
                item["code"],
                item["message"],
                wall_ts=repl_wall_ts_str(),
            )
        )


def _emit_repl_notice_over_prompt(*, prompt: str, buf: str, text: str) -> None:
    sys.stdout.write("\r\033[2K")
    sys.stdout.flush()
    print(text, file=sys.stderr, flush=True)
    sys.stdout.write(prompt + buf)
    sys.stdout.flush()


def _drain_repl_notice_queue_before_blocking_input(notice_q: queue.Queue[str]) -> None:
    while True:
        try:
            text = notice_q.get_nowait()
        except queue.Empty:
            break
        print(text, file=sys.stderr, flush=True)


def _drain_downlink_queue(
    bridge: BackendChatWsBridge,
    outbound_t0: dict[str, float],
) -> None:
    while True:
        item = pop_downlink_item(bridge)
        if item is None:
            break
        _emit_downlink_item(item, outbound_t0)


def _readline_backend_ws_with_sideband(
    bridge: BackendChatWsBridge,
    prompt: str,
    outbound_t0: dict[str, float],
    notice_q: queue.Queue[str],
) -> str:
    """Block for one user line while printing late server-pushed chat frames (POSIX TTY).

    Uses cbreak + no echo and a local buffer so a sideband assistant frame can clear the
    current input line, print the message, then redraw ``prompt`` and any partial input.
    ``notice_q`` carries lines from WebSocket thread callbacks (e.g. ``user_signed_on`` ack)
    so stderr logging does not splice into the same TTY row as the prompt.
    """
    sel = _posix_select_module_for_stdin()
    if sel is None:
        _drain_repl_notice_queue_before_blocking_input(notice_q)
        line = input(prompt)
        _drain_downlink_queue(bridge, outbound_t0)
        return line
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
        drew_prompt_after_notice = False
        while True:
            try:
                n = notice_q.get_nowait()
            except queue.Empty:
                break
            _emit_repl_notice_over_prompt(prompt=prompt, buf=buf, text=n)
            drew_prompt_after_notice = True
        if not drew_prompt_after_notice:
            sys.stdout.write(prompt + buf)
        sys.stdout.flush()

        def redraw_edit_line() -> None:
            sys.stdout.write("\r\033[2K" + prompt + buf)
            sys.stdout.flush()

        def emit_sideband_item(item: Mapping[str, Any]) -> None:
            sys.stdout.write("\r\033[2K")
            sys.stdout.flush()
            print()
            _emit_downlink_item(item, outbound_t0)
            sys.stdout.write(prompt + buf)
            sys.stdout.flush()

        while True:
            try:
                r, _, _ = sel.select(
                    [sys.stdin], [], [], _BACKEND_WS_SIDEBAND_POLL_SEC
                )
            except (ValueError, OSError):
                _drain_repl_notice_queue_before_blocking_input(notice_q)
                line = input(prompt)
                _drain_downlink_queue(bridge, outbound_t0)
                return line
            if not r:
                while True:
                    try:
                        n = notice_q.get_nowait()
                    except queue.Empty:
                        item = pop_downlink_item(bridge)
                        if item is None:
                            break
                        emit_sideband_item(item)
                    else:
                        _emit_repl_notice_over_prompt(prompt=prompt, buf=buf, text=n)
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


def _repl_interactive_backend_ws_loop(
    bridge: BackendChatWsBridge,
    agent_id: str,
    notice_q: queue.Queue[str],
) -> None:
    """Each user line is ``post_turn`` (send-only); assistant/error frames drain via ``pop_downlink_item``.

    Server still processes chat frames in order; multiple ``post_turn`` calls only queue on the wire.
    """
    print(
        f"[{repl_wall_ts_str()}] backend-ws repl (agent_id={agent_id}); "
        "quit / exit / q to leave; history lives on the server. "
        "^D disconnects the bridge (POSIX TTY cbreak path)."
    )
    outbound_t0: dict[str, float] = {}
    while True:
        try:
            line = _readline_backend_ws_with_sideband(
                bridge, "> ", outbound_t0, notice_q
            )
        except EOFError:
            print()
            break
        st = line.strip()
        if st in ("quit", "exit", "q"):
            break
        if not st:
            continue
        msg_uuid = str(uuid.uuid4())
        t_send = time.perf_counter()
        _print_repl_user_input(line, message_uuid=msg_uuid)
        try:
            mid_sent = bridge.post_turn(agent_id, line, msg_uuid)
        except (
            BackendChatWsError,
            TimeoutError,
            OSError,
            RuntimeError,
            ValueError,
        ) as e:
            _print_send_turn_exception(e)
            continue
        outbound_t0[mid_sent] = t_send
        _drain_downlink_queue(bridge, outbound_t0)


def _repl_run_backend_ws_branch(
    *,
    agent_id: str | None,
    api_base_url: str | None,
) -> None:
    agent_resolved = _resolve_chat_agent_id_cli(agent_id)
    base = (api_base_url or default_api_base_url()).strip()
    token = _resolve_bearer_token_cli()
    repl_ws_conn_id = str(uuid.uuid4())
    url = http_base_to_ws_chat_url(
        base, agent_id=agent_resolved, ws_conn_id=repl_ws_conn_id
    )
    logger.info(
        "repl backend-ws api_base={} ws_url={} agent_id={} ws_conn_id={}",
        base,
        url,
        agent_resolved,
        repl_ws_conn_id,
    )
    _init_proto_logging()
    repl_notice_q: queue.Queue[str] = queue.Queue()

    def _user_signed_on_notice(aid: str, message_id: str) -> None:
        repl_notice_q.put(
            f"[{repl_wall_ts_str()}] repl: user_signed_on sent "
            f"(agent_id={aid} message_id={message_id})"
        )

    def _user_signed_on_ack_notice(payload: dict[str, Any]) -> None:
        ok = payload.get("ok")
        reason = payload.get("reason")
        extra = f" reason={reason}" if reason else ""
        repl_notice_q.put(
            f"[{repl_wall_ts_str()}] repl: user_signed_on_ack ok={ok}{extra}"
        )

    def _transport_lost_notice(code: int | None, reason: str) -> None:
        code_part = code if code is not None else "-"
        repl_notice_q.put(
            f"[{repl_wall_ts_str()}] repl: websocket connection lost "
            f"ws_conn_id={repl_ws_conn_id} ws_close_code={code_part} reason={reason!r}"
        )

    def _transport_ready_notice(reconnect: bool) -> None:
        if reconnect:
            msg = "websocket connection restored"
        else:
            msg = "websocket connected"
        repl_notice_q.put(
            f"[{repl_wall_ts_str()}] repl: {msg} ws_conn_id={repl_ws_conn_id}"
        )

    bridge = BackendChatWsBridge(
        ws_url=url,
        bearer_token=token,
        on_user_signed_on_sent=_user_signed_on_notice,
        on_user_signed_on_ack=_user_signed_on_ack_notice,
        on_transport_lost=_transport_lost_notice,
        on_transport_ready=_transport_ready_notice,
    )
    bridge.start()
    try:
        _repl_interactive_backend_ws_loop(bridge, agent_resolved, repl_notice_q)
    finally:
        bridge.stop()


_REPL_APP_HELP = (
    "Inty /api/v1/chat/ws terminal client.\n\n"
    "Each assistant downlink prints a metadata section (one line): wall clock, source label, "
    "elapsed ms, correlation key=value tokens from meta_data, optional LangSmith UI URLs, "
    "and optional tool_background_started=true. Additional lines after the assistant body "
    "may include local-path: (tool_bg) or image-url: (generated image) metadata."
)

app = App(
    name="inty-chat-ws-repl",
    help=_REPL_APP_HELP,
)


@app.command
def repl(
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
    _repl_run_backend_ws_branch(
        agent_id=agent_id,
        api_base_url=api_base_url,
    )


if __name__ == "__main__":
    app()
