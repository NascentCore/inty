"""
Smoke 测试 /api/v1/chat/ws（与 HTTP chat completions 同一条处理链）。

在仓库根目录、已安装依赖的虚拟环境下运行，例如:
  INTY_BEARER_TOKEN=xxx python3 .cursor/skills/inty-server-module-verify/scripts/test_chat_ws.py \\
    --api-base http://127.0.0.1:8000 --agent-id <AGENT_ID>

创建新 agent 再测（无需事先填写 agent_id）:
  ... test_chat_ws.py --api-base http://127.0.0.1:8000 --create-agent
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedError

_REPO_ROOT: Path | None = None

# Final-line marker so humans and agents can grep / summarize without parsing assistant body text.
_VERIFY_TAG = "[inty-server-module-verify]"


def _emit_verify_result(
    *,
    ok: bool,
    exit_code: int,
    detail: str = "",
    elapsed_s: float | None = None,
) -> None:
    """Print one explicit PASS/FAIL line as the conclusion (stderr for failures)."""
    if ok:
        timing = f", elapsed={elapsed_s:.2f}s" if elapsed_s is not None else ""
        print(f"{_VERIFY_TAG} RESULT: PASS (exit={exit_code}{timing})", flush=True)
    else:
        suffix = f" — {detail}" if detail else ""
        print(
            f"{_VERIFY_TAG} RESULT: FAIL (exit={exit_code}){suffix}",
            file=sys.stderr,
            flush=True,
        )


def _find_repo_root() -> Path:
    """Inty 仓库根：须含 app/ 与 tools/，避免误把本 skill 子目录（也有 requirements.txt）当作根。"""
    here = Path(__file__).resolve()
    for p in (here, *here.parents):
        if (p / "pyproject.toml").is_file() and (p / "app").is_dir():
            return p
    for p in (here, *here.parents):
        if (p / "requirements.txt").is_file() and (p / "app").is_dir() and (p / "tools").is_dir():
            return p
    raise RuntimeError("Cannot find Inty repo root (expected pyproject.toml + app/ above script).")


def _ensure_sys_path() -> Path:
    global _REPO_ROOT
    if _REPO_ROOT is not None:
        return _REPO_ROOT
    root = _find_repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    _REPO_ROOT = root
    return root


def _load_yaml_config(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError as e:
        raise SystemExit("PyYAML is required for --config. pip install pyyaml") from e
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise SystemExit("config file must be a mapping at the top level")
    return {str(k): v for k, v in raw.items()}


def _str_opt(cfg: dict[str, Any], key: str) -> str | None:
    v = cfg.get(key)
    if v is None or v == "":
        return None
    if not isinstance(v, str):
        return str(v)
    return v


def _bool_opt(cfg: dict[str, Any], key: str) -> bool | None:
    v = cfg.get(key)
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    raise SystemExit(f"config key {key!r} must be a boolean")


def _float_opt(cfg: dict[str, Any], key: str) -> float | None:
    v = cfg.get(key)
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    raise SystemExit(f"config key {key!r} must be a number")


def _http_post_json(
    *,
    url: str,
    body: dict[str, Any],
    bearer_token: str,
    timeout: float,
) -> dict[str, Any]:
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {bearer_token.strip()}",
        },
        method="POST",
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as err:
            raise RuntimeError(f"HTTP {e.code}: {raw[:800]}") from err
    return json.loads(raw)


def _create_smoke_agent(
    *,
    api_base: str,
    bearer_token: str,
    http_timeout: float,
) -> str:
    base = api_base.rstrip("/")
    url = f"{base}/api/v1/ai/agents"
    tag = uuid.uuid4().hex[:10]
    body: dict[str, Any] = {
        "name": f"inty-ws-verify-{tag}",
        "gender": "FEMALE",
        "visibility": "PRIVATE",
        "intro": "Temporary agent for inty-server-module-verify smoke test.",
        "opening": "Hello.",
        "personality": "Friendly and brief.",
        "scenario": "Automated verification only.",
    }
    out = _http_post_json(url=url, body=body, bearer_token=bearer_token, timeout=http_timeout)
    if out.get("code") != 200:
        msg = out.get("message", "")
        data = out.get("data")
        extra = ""
        if isinstance(data, dict):
            ec = data.get("error_code")
            if ec:
                extra = f" error_code={ec!r}"
            lim = data.get("limit")
            used = data.get("used_count")
            if lim is not None:
                extra += f" used_count={used!r} limit={lim!r}"
        raise RuntimeError(f"create agent failed: code={out.get('code')} message={msg!r}{extra}")
    data = out.get("data")
    if not isinstance(data, dict) or not data.get("id"):
        raise RuntimeError(f"create agent: unexpected response: {out!r}")
    return str(data["id"])


async def _turn_simple(
    *,
    http_base: str,
    bearer_token: str,
    agent_id: str,
    user_text: str,
    connect_timeout: float,
) -> str:
    _ensure_sys_path()
    from tools.inty_v2_repl.backend_chat_ws import chat_turn_single_http_base

    return await chat_turn_single_http_base(
        http_base=http_base,
        bearer_token=bearer_token,
        agent_id=agent_id,
        user_text=user_text,
        connect_timeout=connect_timeout,
        proxy=None,
    )


async def _turn_with_connect_kickoff(
    *,
    http_base: str,
    bearer_token: str,
    agent_id: str,
    user_text: str,
    connect_timeout: float,
    recv_timeout: float,
    kickoff_drain_sec: float = 5.0,
) -> str:
    _ensure_sys_path()
    from app.schemas.chat import ChatCompletionRequest, ChatMessage, ChatWebSocketRequest
    from tools.inty_v2_repl.backend_chat_ws import (
        _parse_chat_response_payload,
        http_base_to_ws_chat_url,
    )

    url = http_base_to_ws_chat_url(http_base, agent_id=agent_id)
    headers = [("Authorization", f"Bearer {bearer_token.strip()}")]

    async with websockets.connect(
        url,
        additional_headers=headers,
        open_timeout=connect_timeout,
        ping_interval=None,
        proxy=None,
    ) as ws:
        # 若服务端会先发 interactive kickoff，先收掉一帧再发用户轮次
        try:
            raw0 = await asyncio.wait_for(ws.recv(), timeout=kickoff_drain_sec)
        except TimeoutError:
            pass
        else:
            data0 = json.loads(raw0)
            if data0.get("type") == "pong":
                pass
            else:
                c = data0.get("code")
                if c is not None and int(c) != 200:
                    _parse_chat_response_payload(data0)  # raises BackendChatWsError
                # code 200: 视为 kickoff，丢弃
        req = ChatWebSocketRequest(
            agent_id=agent_id,
            request=ChatCompletionRequest(
                messages=[ChatMessage(role="user", content=user_text)],
                message_id=str(uuid.uuid4()),
            ),
        )
        await ws.send(req.model_dump_json(by_alias=True))
        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=recv_timeout)
            data = json.loads(raw)
            if data.get("type") == "pong":
                continue
            return _parse_chat_response_payload(data)


def _default_recv_timeout() -> float:
    _ensure_sys_path()
    from tools.inty_v2_repl.backend_chat_ws import default_recv_timeout_sec

    return default_recv_timeout_sec()


async def _run(args: argparse.Namespace) -> int:
    _ensure_sys_path()
    from tools.inty_v2_repl.backend_chat_ws import BackendChatWsError

    cfg: dict[str, Any] = {}
    if args.config:
        p = Path(args.config).expanduser().resolve()
        if not p.is_file():
            print(f"config not found: {p}", file=sys.stderr)
            _emit_verify_result(ok=False, exit_code=2, detail=f"config not found: {p}")
            return 2
        cfg = _load_yaml_config(p)

    api_base = (
        (args.api_base or "").strip()
        or os.environ.get("INTY_API_BASE_URL", "").strip()
        or (_str_opt(cfg, "api_base_url") or "")
    )
    if not api_base:
        print("Missing api base: use --api-base, INTY_API_BASE_URL, or config api_base_url", file=sys.stderr)
        _emit_verify_result(
            ok=False,
            exit_code=2,
            detail="missing api base URL",
        )
        return 2

    create_agent = bool(args.create_agent) or (_bool_opt(cfg, "create_agent") is True)

    agent_id_cli = (args.agent_id or "").strip() or (_str_opt(cfg, "agent_id") or "").strip()
    if create_agent and agent_id_cli:
        print(
            f"Ignoring --agent-id / config agent_id ({agent_id_cli!r}); using newly created agent (--create-agent).",
            file=sys.stderr,
        )

    user_message = (args.message or "").strip() or _str_opt(cfg, "user_message")
    if not user_message:
        user_message = "你好，简单回复即可。"

    use_kickoff: bool
    if args.connect_kickoff:
        use_kickoff = True
    else:
        bo = _bool_opt(cfg, "connect_kickoff")
        use_kickoff = bool(bo) if bo is not None else False

    token = (
        (args.token or "").strip()
        or os.environ.get("INTY_BEARER_TOKEN", "").strip()
        or (_str_opt(cfg, "bearer_token") or "").strip()
    )
    if not token:
        print(
            "Missing token: use --token, or set INTY_BEARER_TOKEN in the integrated terminal, "
            "or add bearer_token to a local config (see config.example.yaml).",
            file=sys.stderr,
        )
        _emit_verify_result(ok=False, exit_code=2, detail="missing bearer token")
        return 2

    cto = _float_opt(cfg, "connect_timeout_sec")
    connect_timeout = cto if cto is not None else 30.0
    rto = _float_opt(cfg, "recv_timeout_sec")
    recv_timeout = rto if rto is not None else _default_recv_timeout()
    hto = _float_opt(cfg, "create_agent_http_timeout_sec")
    http_post_timeout = hto if hto is not None else max(60.0, connect_timeout)

    agent_id: str
    if create_agent:
        try:
            agent_id = _create_smoke_agent(
                api_base=api_base,
                bearer_token=token,
                http_timeout=http_post_timeout,
            )
        except Exception as e:
            print(f"Create agent: {e}", file=sys.stderr)
            _emit_verify_result(ok=False, exit_code=2, detail=str(e))
            return 2
        print(f"{_VERIFY_TAG} created_agent_id={agent_id}", flush=True)
    else:
        agent_id = agent_id_cli
        if not agent_id:
            print("Missing --agent-id or config agent_id (or use --create-agent / create_agent: true)", file=sys.stderr)
            _emit_verify_result(ok=False, exit_code=2, detail="missing agent_id")
            return 2

    t0 = time.perf_counter()
    try:
        if use_kickoff:
            text = await _turn_with_connect_kickoff(
                http_base=api_base,
                bearer_token=token,
                agent_id=agent_id,
                user_text=user_message,
                connect_timeout=connect_timeout,
                recv_timeout=recv_timeout,
            )
        else:
            text = await _turn_simple(
                http_base=api_base,
                bearer_token=token,
                agent_id=agent_id,
                user_text=user_message,
                connect_timeout=connect_timeout,
            )
    except ConnectionClosed as e:
        if e.code == 4001:
            print("WebSocket closed: 4001 Unauthorized (check INTY_BEARER_TOKEN).", file=sys.stderr)
            _emit_verify_result(ok=False, exit_code=1, detail="WebSocket 4001 Unauthorized")
        else:
            print(f"WebSocket closed: code={e.code} reason={e.reason!r}", file=sys.stderr)
            _emit_verify_result(
                ok=False,
                exit_code=1,
                detail=f"WebSocket closed code={e.code}",
            )
        return 1
    except ConnectionClosedError as e:
        print(f"WebSocket error: {e}", file=sys.stderr)
        _emit_verify_result(ok=False, exit_code=1, detail="WebSocket connection error")
        return 1
    except BackendChatWsError as e:
        print(
            f"Chat error: code={e.code} message={e.agent_message!r} agent_id={e.agent_id!r}",
            file=sys.stderr,
        )
        _emit_verify_result(
            ok=False,
            exit_code=1,
            detail=f"API error code={e.code}",
        )
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        _emit_verify_result(ok=False, exit_code=1, detail=str(e))
        return 1
    elapsed = time.perf_counter() - t0
    print(f"OK ({elapsed:.2f}s)\n")
    print(text)
    _emit_verify_result(ok=True, exit_code=0, elapsed_s=elapsed)
    return 0


def main() -> None:
    p = argparse.ArgumentParser(
        description="Smoke test WebSocket /api/v1/chat/ws (companion chat one turn)"
    )
    p.add_argument("--config", "-c", help="YAML config (see config.example.yaml)")
    p.add_argument("--api-base", help="e.g. http://127.0.0.1:8000 (or INTY_API_BASE_URL)")
    p.add_argument("--token", help="Bearer token; prefer INTY_BEARER_TOKEN")
    p.add_argument("--agent-id", help="Agent id (not required when --create-agent)")
    p.add_argument(
        "--create-agent",
        action="store_true",
        help="POST /api/v1/ai/agents to create a PRIVATE agent, then run this smoke test with returned id",
    )
    p.add_argument("--message", "-m", help="User message for one turn")
    p.add_argument(
        "--connect-kickoff",
        action="store_true",
        help="Pass agent_id in WS URL so server may send kickoff; drain one frame then send",
    )
    args = p.parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
