"""Cyclopts entry: Inty backend WebSocket REPL only (no local workspace turn loop)."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Annotated, Mapping

from cyclopts import App, Parameter
from dotenv import load_dotenv
from loguru import logger

_PKG_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PKG_DIR.parent.parent
if __package__ is None:
    sys.path.insert(0, str(_PKG_DIR.parent))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.inty_v2_repl.client import load_prototype_dotenv
from tools.inty_v2_repl.backend_chat_ws import (
    BackendChatWsBridge,
    BackendChatWsError,
    default_api_base_url,
    http_base_to_ws_chat_url,
)
from tools.inty_v2_repl.jsonl_db_store import (
    flush_jsonl_db_store,
    shutdown_jsonl_db_store,
)
from tools.inty_v2_repl.llm_trace import configure_llm_trace_file
from tools.inty_v2_repl.memory_store_registry import (
    flush_memory_store,
    shutdown_memory_store,
)
from tools.inty_v2_repl.proto_log import (
    configure_proto_log,
    repl_wall_ts_str,
    resolve_proto_log_file,
)

load_prototype_dotenv()
load_dotenv(_REPO_ROOT / ".env")


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


def _configure_llm_trace_for_workspace(root: Path) -> None:
    configure_llm_trace_file(root.resolve() / "llm_trace.jsonl")


def _print_openrouter_invalid_json_retry_hint() -> None:
    print(f"[{repl_wall_ts_str()}] LLM API 临时异常（上游返回非 JSON），请重试。")


def _flush_and_shutdown_memory_store(root: Path) -> None:
    flush_memory_store(root, timeout_s=5.0)
    flush_jsonl_db_store(timeout_s=5.0)
    shutdown_memory_store(root, timeout_s=5.0)
    shutdown_jsonl_db_store(timeout_s=5.0)


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
    t = os.environ.get("INTY_ACCESS_TOKEN", "").strip()
    if t:
        return t
    raise SystemExit("repl requires INTY_ACCESS_TOKEN (Bearer JWT for the backend)")


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
        except (TimeoutError, OSError, RuntimeError, ValueError) as exc:
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
    help="Inty 后端 WebSocket 终端对话（/api/v1/chat/ws）；本地目录仅用于日志与 llm_trace。",
)


@app.command
def repl(
    workspace: Annotated[
        Path | None,
        Parameter(
            name="--workspace",
            help="日志与 llm_trace.jsonl 目录；默认包内 workspace/",
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


sys.modules.setdefault("inty_v2_text_chat_prototype.main", sys.modules[__name__])

if __name__ == "__main__":
    app()
