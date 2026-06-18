#!/usr/bin/env python3
"""Automated local Ops + WebSocket regression for companion queue-serving.

Skill smoke driver (not ``app/`` production code). Drives bootstrap turns, one
settled user turn, and waits for inner-tick proactive chat via
``BackendChatWsBridge`` (same transport as ``inty_v2_repl``). Writes a JSON
report under ``tmp/`` and prints a one-line SUMMARY.

Layout:
- Driver: ``run_regression`` / ``main`` for end-to-end WS and Postgres checks.
- Strict-mode DB verification: below ``_is_inner_tick_proactive``; when no
  proactive WS frame arrives, it queries ``chat_history`` for silent inner ticks.
  ``_parse_proactive_chat_history_rows`` is unit-tested in
  ``tests/cursor/skills/scripts/test_run_inty_repl_regression.py``.

Run with shell cwd = repository root (or any path under the repo).
"""

from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

_TAG = "[inty-repl-regression]"
_DEFAULT_API_BASE = "http://127.0.0.1:8001"
_DEFAULT_CONFIG = "devops/config.yaml.local"
_DEFAULT_USER_ID = "user-testing"
_PROACTIVE_CHAT_HISTORY_MARKER = "[SYSTEM PROACTIVE CHAT]"
_DEFAULT_BOOTSTRAP_TURNS = (
    "who are you?",
    "用中文吧",
    "你叫我 大雄",
    "你叫 多啦",
    "旁边有人就行",
)
_DEFAULT_BOOTSTRAP_FINISH_TURN = (
    "引导可以结束了。请把 USER、IDENTITY、STYLE 写好，然后调用 "
    "companion_bootstrap_user_interactive_complete 完成引导。"
)
_DEFAULT_SETTLED_TURN = "今天天气怎么样？"
_RECV_POLL_SEC = 0.25
_TURN_REPLY_TIMEOUT_SEC = 180.0
_TURN_TRAILING_QUIET_SEC = 5.0


@dataclass(frozen=True)
class ProactiveChatHistoryRow:
    """Synthetic proactive user row observed in ``chat_history`` after the run starts."""

    chat_history_id: str
    content_preview: str
    created_at: str
    has_assistant_reply: bool


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in (here, *here.parents):
        if (p / "pyproject.toml").is_file() and (p / "app").is_dir():
            return p
    for p in (here, *here.parents):
        if (
            (p / "requirements.txt").is_file()
            and (p / "app").is_dir()
            and (p / "tools").is_dir()
        ):
            return p
    raise RuntimeError("Cannot find Inty repo root above script path.")


def _ensure_import_path(repo_root: Path) -> None:
    root_s = str(repo_root)
    if root_s not in sys.path:
        sys.path.insert(0, root_s)


def _read_bearer(repo_root: Path, token_path: str) -> str:
    p = Path(token_path)
    if not p.is_absolute():
        p = repo_root / p
    tok = p.read_text(encoding="utf-8").strip()
    assert tok != ""
    return tok


def _create_agent_id(
    *,
    repo_root: Path,
    api_base: str,
    token_path: str,
    http_timeout: float,
    stderr: TextIO,
) -> str:
    from tools.scripts.create_bootstrap_test_agent import run_create

    buf = io.StringIO()
    rc = run_create(
        api_base=api_base,
        token_path=token_path,
        http_timeout=http_timeout,
        stdout=buf,
        stderr=stderr,
    )
    if rc != 0:
        raise RuntimeError("create_bootstrap_test_agent failed")
    for line in buf.getvalue().splitlines():
        if line.startswith("[create-bootstrap-test-agent] agent_id="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("create_bootstrap_test_agent did not print agent_id")


def _wait_downlink(
    bridge: Any,
    *,
    timeout_sec: float,
    label: str,
) -> tuple[str | None, dict[str, Any], tuple[int, str] | None]:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        text, err, meta = bridge.try_pop_queued_chat()
        if err is not None:
            return None, {}, err
        if text is not None:
            return text, meta, None
        time.sleep(_RECV_POLL_SEC)
    return None, {}, (408, f"timeout waiting for {label}")


def _drain_until_quiet(
    bridge: Any,
    *,
    quiet_sec: float,
    max_sec: float,
) -> list[tuple[str, dict[str, Any]]]:
    deadline = time.monotonic() + max_sec
    last_at = time.monotonic()
    out: list[tuple[str, dict[str, Any]]] = []
    while time.monotonic() < deadline:
        text, err, meta = bridge.try_pop_queued_chat()
        if err is not None:
            out.append((f"[error {err[0]}: {err[1]}]", {}))
            last_at = time.monotonic()
        elif text is not None:
            out.append((text, meta))
            last_at = time.monotonic()
        elif time.monotonic() - last_at >= quiet_sec:
            break
        else:
            time.sleep(_RECV_POLL_SEC)
    return out


def _record_trailing_downlink(
    report: dict[str, Any],
    *,
    label: str,
    text: str,
    meta: dict[str, Any],
) -> None:
    report["turns"].append(
        {
            "kind": f"{label}_trailing",
            "text_preview": text[:120],
            "meta": meta,
        }
    )
    kind = meta.get("source") or meta.get("inner_tick_activity")
    print(
        f"{_TAG} {label} trailing downlink source={kind!r} text={text[:60]!r}",
        flush=True,
    )


def _drain_turn_trailing_frames(
    bridge: Any,
    report: dict[str, Any],
    *,
    label: str,
) -> None:
    """Drain interim OutputQueue WS frames until the turn is quiet (multi-round tool loop)."""
    trailing = _drain_until_quiet(
        bridge,
        quiet_sec=_TURN_TRAILING_QUIET_SEC,
        max_sec=_TURN_REPLY_TIMEOUT_SEC,
    )
    for text, meta in trailing:
        _record_trailing_downlink(report, label=label, text=text, meta=meta)


def _send_turn(bridge: Any, agent_id: str, text: str) -> str:
    msg_uuid = str(uuid.uuid4())
    bridge.post_turn(agent_id, text, msg_uuid)
    return msg_uuid


def _psql(repo_root: Path, config_path: Path, query: str) -> str:
    import yaml

    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    db = cfg["database"]
    env = {**dict(os.environ), "PGPASSWORD": str(db["password"])}
    cmd = [
        "psql",
        "-h",
        str(db["host"]),
        "-p",
        str(db["port"]),
        "-U",
        str(db["user"]),
        "-d",
        str(db["db"]),
        "-t",
        "-A",
        "-c",
        query,
    ]
    return subprocess.check_output(cmd, env=env, text=True, cwd=repo_root)


def _is_inner_tick_proactive(meta: dict[str, Any]) -> bool:
    if meta.get("source") == "greeting":
        return False
    activity = str(meta.get("inner_tick_activity") or "").strip()
    if activity == "proactive_chat":
        return True
    if meta.get("source") == "inner_tick" and activity == "proactive_chat":
        return True
    lane = str(meta.get("companion_turn_lane") or "").strip()
    return lane == "inner_tick" and activity == "proactive_chat"


# --- strict-mode DB verification (unit-tested; see tests/cursor/skills/scripts/) ---


def _query_proactive_chat_history_rows(
    repo_root: Path,
    config_path: Path,
    *,
    user_id: str,
    agent_id: str,
    run_started_at_utc: datetime,
) -> list[ProactiveChatHistoryRow]:
    """Regression-only: load synthetic proactive ``chat_history`` rows from Postgres."""
    assert user_id != ""
    assert agent_id != ""
    scope_chat = f"agent-scope:{user_id}:{agent_id}"
    session_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, scope_chat))
    since = run_started_at_utc.isoformat()
    raw = _psql(
        repo_root,
        config_path,
        f"""
WITH proactive AS (
  SELECT ch.id,
         left(ch.message->'data'->>'content', 120) AS content_preview,
         ch.created_at,
         lead(ch.id) OVER (ORDER BY ch.id) AS next_proactive_id
  FROM chat_history ch
  WHERE ch.session_id = '{session_id}'
    AND ch.created_at >= timestamptz '{since}'
    AND ch.meta_data->>'companion_proactive_chat' = 'true'
    AND ch.meta_data->>'inner_tick' = 'true'
    AND ch.message->'data'->>'content' LIKE '{_PROACTIVE_CHAT_HISTORY_MARKER}%'
)
SELECT json_build_object(
       'chat_history_id', proactive.id::text,
       'content_preview', proactive.content_preview,
       'created_at', proactive.created_at::text,
       'has_assistant_reply', EXISTS (
           SELECT 1
           FROM chat_history ai
           WHERE ai.session_id = '{session_id}'
             AND ai.message->>'type' = 'ai'
             AND ai.id > proactive.id
             AND (
               proactive.next_proactive_id IS NULL
               OR ai.id < proactive.next_proactive_id
             )
       ))
FROM proactive
ORDER BY proactive.id;
""",
    )
    return _parse_proactive_chat_history_rows(raw)


def _parse_proactive_chat_history_rows(raw: str) -> list[ProactiveChatHistoryRow]:
    """Regression-only parser for ``_query_proactive_chat_history_rows`` JSON lines."""
    rows: list[ProactiveChatHistoryRow] = []
    for line in raw.strip().splitlines():
        if not line.strip():
            continue
        raw_row = json.loads(line)
        rows.append(
            ProactiveChatHistoryRow(
                chat_history_id=str(raw_row["chat_history_id"]),
                content_preview=str(raw_row["content_preview"]),
                created_at=str(raw_row["created_at"]),
                has_assistant_reply=bool(raw_row["has_assistant_reply"]),
            )
        )
    return rows


def _record_proactive_from_db(
    report: dict[str, Any],
    rows: list[ProactiveChatHistoryRow],
) -> None:
    for row in rows:
        report["proactive"].append(
            {
                "text_preview": row.content_preview,
                "meta": {
                    "source": "db_chat_history",
                    "chat_history_id": row.chat_history_id,
                    "inner_tick_activity": "proactive_chat",
                },
                "silent": not row.has_assistant_reply,
                "created_at": row.created_at,
            }
        )
        print(
            f"{_TAG} proactive observed (db) chat_history_id={row.chat_history_id} "
            f"silent={not row.has_assistant_reply} "
            f"preview={row.content_preview[:60]!r}",
            flush=True,
        )


def run_regression(
    *,
    repo_root: Path,
    agent_id: str,
    api_base: str,
    config_path: Path,
    user_id: str,
    bootstrap_turns: tuple[str, ...],
    bootstrap_finish_turn: str,
    settled_turn: str,
    proactive_wait_sec: float,
    report_path: Path,
    token_path: str,
    strict: bool,
    stderr: TextIO,
) -> int:
    _ensure_import_path(repo_root)
    from tools.inty_v2_repl.backend_chat_ws import (
        BackendChatWsBridge,
        http_base_to_ws_chat_url,
    )

    bearer = _read_bearer(repo_root, token_path)
    ws_url = http_base_to_ws_chat_url(
        api_base,
        agent_id=agent_id,
        ws_conn_id=str(uuid.uuid4()),
    )
    bridge = BackendChatWsBridge(ws_url=ws_url, bearer_token=bearer)
    report: dict[str, Any] = {
        "agent_id": agent_id,
        "turns": [],
        "proactive": [],
        "errors": [],
    }
    print(f"{_TAG} agent_id={agent_id}", flush=True)
    run_started_at_utc = datetime.now(timezone.utc)
    bridge.start(connect_timeout=45.0)
    try:
        print(f"{_TAG} waiting for implicit greeting...", flush=True)
        for text, meta in _drain_until_quiet(
            bridge, quiet_sec=3.0, max_sec=_TURN_REPLY_TIMEOUT_SEC
        ):
            report["turns"].append(
                {"kind": "greeting", "text_preview": text[:120], "meta": meta}
            )
            print(
                f"{_TAG} greeting text={text[:80]!r} "
                f"langsmith_trace_id={meta.get('langsmith_trace_id')}",
                flush=True,
            )

        for idx, user_text in enumerate(bootstrap_turns, start=1):
            print(f"{_TAG} bootstrap turn {idx}: {user_text!r}", flush=True)
            _send_turn(bridge, agent_id, user_text)
            text, meta, err = _wait_downlink(
                bridge,
                timeout_sec=_TURN_REPLY_TIMEOUT_SEC,
                label=f"bootstrap-{idx}",
            )
            if err is not None:
                report["errors"].append({"turn": f"bootstrap-{idx}", "error": err})
                print(f"{_TAG} ERROR bootstrap-{idx}: {err}", file=stderr, flush=True)
                continue
            assert text is not None
            report["turns"].append(
                {
                    "kind": "bootstrap",
                    "user": user_text,
                    "text_preview": text[:120],
                    "meta": meta,
                }
            )
            print(
                f"{_TAG} reply preview={text[:80]!r} "
                f"context_mode={meta.get('context_mode')}",
                flush=True,
            )
            _drain_until_quiet(bridge, quiet_sec=2.0, max_sec=15.0)

        print(f"{_TAG} bootstrap finish turn: {bootstrap_finish_turn!r}", flush=True)
        _send_turn(bridge, agent_id, bootstrap_finish_turn)
        text, meta, err = _wait_downlink(
            bridge,
            timeout_sec=_TURN_REPLY_TIMEOUT_SEC,
            label="bootstrap-finish",
        )
        if err is not None:
            report["errors"].append({"turn": "bootstrap-finish", "error": err})
            print(f"{_TAG} ERROR bootstrap-finish: {err}", file=stderr, flush=True)
        else:
            assert text is not None
            report["turns"].append(
                {
                    "kind": "bootstrap_finish",
                    "user": bootstrap_finish_turn,
                    "text_preview": text[:120],
                    "meta": meta,
                }
            )
            print(
                f"{_TAG} bootstrap-finish reply={text[:80]!r} "
                f"context_mode={meta.get('context_mode')}",
                flush=True,
            )
        _drain_turn_trailing_frames(bridge, report, label="bootstrap-finish")

        print(f"{_TAG} settled turn: {settled_turn!r}", flush=True)
        _send_turn(bridge, agent_id, settled_turn)
        text, meta, err = _wait_downlink(
            bridge,
            timeout_sec=_TURN_REPLY_TIMEOUT_SEC,
            label="settled",
        )
        if err is not None:
            report["errors"].append({"turn": "settled", "error": err})
            print(f"{_TAG} ERROR settled: {err}", file=stderr, flush=True)
        else:
            assert text is not None
            report["turns"].append(
                {
                    "kind": "settled",
                    "user": settled_turn,
                    "text_preview": text[:120],
                    "meta": meta,
                }
            )
            print(
                f"{_TAG} settled reply={text[:80]!r} "
                f"langsmith_trace_id={meta.get('langsmith_trace_id')}",
                flush=True,
            )
        _drain_turn_trailing_frames(bridge, report, label="settled")

        print(
            f"{_TAG} waiting up to {proactive_wait_sec}s for inner-tick proactive...",
            flush=True,
        )
        proactive_deadline = time.monotonic() + proactive_wait_sec
        while time.monotonic() < proactive_deadline:
            text, meta, err = _wait_downlink(
                bridge,
                timeout_sec=min(10.0, proactive_deadline - time.monotonic()),
                label="proactive",
            )
            if err is not None and err[0] == 408:
                continue
            if err is not None:
                report["errors"].append({"turn": "proactive", "error": err})
                break
            if text is None:
                continue
            if not _is_inner_tick_proactive(meta):
                kind = meta.get("source") or meta.get("inner_tick_activity")
                if str(meta.get("source") or "") == "chat":
                    _record_trailing_downlink(
                        report,
                        label="proactive_wait_late",
                        text=text,
                        meta=meta,
                    )
                else:
                    print(
                        f"{_TAG} ignore non-proactive downlink source={kind!r}",
                        flush=True,
                    )
                continue
            report["proactive"].append(
                {
                    "text_preview": text[:120],
                    "meta": meta,
                    "silent": text.strip() == "[SILENT]",
                }
            )
            print(
                f"{_TAG} proactive text={text[:80]!r} "
                f"langsmith_trace_id={meta.get('langsmith_trace_id')}",
                flush=True,
            )
    finally:
        bridge.stop()

    scope_chat = f"agent-scope:{user_id}:{agent_id}"
    ctx_rows = _psql(
        repo_root,
        config_path,
        f"""
SELECT sequence_id,
       trim(content)::json->>'context_mode' AS context_mode,
       trim(content)::json->>'workspace_bootstrap_user_interactive_completed' AS bootstrap_completed
FROM companion_memory_document_versions
WHERE companion_id = '{agent_id}'
  AND user_id = '{user_id}'
  AND chat_id = '{scope_chat}'
  AND document_kind = 'context_json'
  AND calendar_date IS NULL
ORDER BY sequence_id DESC
LIMIT 3;
""",
    )
    in_q = _psql(
        repo_root,
        config_path,
        f"SELECT status, COUNT(*) FROM agentic_companion_input_queue "
        f"WHERE agent_id = '{agent_id}' GROUP BY status ORDER BY status;",
    )
    out_q = _psql(
        repo_root,
        config_path,
        f"SELECT status, COUNT(*) FROM agentic_companion_output_queue "
        f"WHERE agent_id = '{agent_id}' GROUP BY status ORDER BY status;",
    )
    out_latest = _psql(
        repo_root,
        config_path,
        f"""
SELECT sequence_id, status, batch_id, left(text, 80), langsmith_trace_id, langsmith_run_id
FROM agentic_companion_output_queue
WHERE agent_id = '{agent_id}'
ORDER BY sequence_id DESC
LIMIT 8;
""",
    )

    report["db"] = {
        "context_json": ctx_rows.strip(),
        "input_queue": in_q.strip(),
        "output_queue": out_q.strip(),
        "output_latest": out_latest.strip(),
    }

    if not report["proactive"]:
        proactive_rows = _query_proactive_chat_history_rows(
            repo_root,
            config_path,
            user_id=user_id,
            agent_id=agent_id,
            run_started_at_utc=run_started_at_utc,
        )
        if proactive_rows:
            report["db"]["proactive_chat_history"] = [
                {
                    "chat_history_id": row.chat_history_id,
                    "content_preview": row.content_preview,
                    "created_at": row.created_at,
                    "silent": not row.has_assistant_reply,
                }
                for row in proactive_rows
            ]
            _record_proactive_from_db(report, proactive_rows)

    ctx_line = ctx_rows.strip().split("\n")[0] if ctx_rows.strip() else ""
    parts = ctx_line.split("|") if ctx_line else []
    bootstrap_done = parts[2] if len(parts) >= 3 else "unknown"
    context_mode = parts[1] if len(parts) >= 2 else "unknown"

    proactive_present = bool(report["proactive"])
    settled_ok = any(
        t.get("kind") == "settled" and t.get("text_preview") for t in report["turns"]
    )
    in_all_delivered = (
        "pending" not in in_q and "failed" not in in_q and bool(in_q.strip())
    )
    out_all_delivered = (
        "pending" not in out_q and "failed" not in out_q and bool(out_q.strip())
    )

    summary = {
        "bootstrap": "complete" if bootstrap_done == "true" else "incomplete",
        "context_mode": context_mode,
        "settled_queue_turn": "pass" if settled_ok and not report["errors"] else "fail",
        "proactive_inner_tick": "present" if proactive_present else "missing",
        "input_queue_counts": in_q.strip(),
        "output_queue_counts": out_q.strip(),
        "input_all_delivered": in_all_delivered,
        "output_all_delivered": out_all_delivered,
    }
    report["summary"] = summary

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"{_TAG} report written to {report_path}", flush=True)
    print(f"{_TAG} SUMMARY: {json.dumps(summary, ensure_ascii=False)}", flush=True)

    queue_ok = (
        settled_ok
        and not report["errors"]
        and in_all_delivered
        and out_all_delivered
    )
    if strict:
        strict_ok = (
            queue_ok
            and bootstrap_done == "true"
            and proactive_present
        )
        return 0 if strict_ok else 1
    return 0 if queue_ok else 1


def main(argv: list[str] | None = None) -> int:
    repo_root = _find_repo_root()
    default_api = (
        os.environ.get("INTY_API_BASE_URL") or ""
    ).strip() or _DEFAULT_API_BASE
    default_token = (
        os.environ.get("INTY_OPS_BEARER_TOKEN_FILE") or ""
    ).strip() or ".inty_ops_bearer_token"
    default_config = (
        os.environ.get("INTY_CONFIG_YAML") or ""
    ).strip() or _DEFAULT_CONFIG

    p = argparse.ArgumentParser(
        description="Automated Ops WebSocket regression for companion queue-serving."
    )
    p.add_argument(
        "--agent-id",
        default="",
        help="Existing bootstrap test agent id (required unless --create-agent)",
    )
    p.add_argument(
        "--create-agent",
        action="store_true",
        help="POST a fresh PRIVATE agent before the regression run",
    )
    p.add_argument(
        "--api-base",
        default=default_api,
        help=f"Ops HTTP base (default: $INTY_API_BASE_URL or {_DEFAULT_API_BASE})",
    )
    p.add_argument(
        "--config",
        default=default_config,
        help=f"YAML for Postgres DSN (default: $INTY_CONFIG_YAML or {_DEFAULT_CONFIG})",
    )
    p.add_argument(
        "--token-file",
        default=default_token,
        help="Bearer token file relative to repo root",
    )
    p.add_argument(
        "--user-id",
        default=_DEFAULT_USER_ID,
        help=f"Local superuser id for agent-scope queries (default: {_DEFAULT_USER_ID})",
    )
    p.add_argument(
        "--proactive-wait-sec",
        type=float,
        default=120.0,
        help="Seconds to wait for inner-tick proactive after settled turn",
    )
    p.add_argument(
        "--report",
        default="",
        help="JSON report path (default: tmp/repl-regression-<agent_id>.json)",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="Also require bootstrap complete and proactive inner-tick",
    )
    p.add_argument(
        "--create-timeout",
        type=float,
        default=60.0,
        help="HTTP timeout for --create-agent (default 60)",
    )
    args = p.parse_args(argv)

    _ensure_import_path(repo_root)
    agent_id = str(args.agent_id).strip()
    if args.create_agent:
        if agent_id:
            print(
                f"{_TAG} warning: --agent-id ignored when --create-agent is set",
                file=sys.stderr,
            )
        agent_id = _create_agent_id(
            repo_root=repo_root,
            api_base=str(args.api_base).strip(),
            token_path=str(args.token_file).strip(),
            http_timeout=float(args.create_timeout),
            stderr=sys.stderr,
        )
    if not agent_id:
        print("error: pass --agent-id or --create-agent", file=sys.stderr)
        return 2

    config_path = Path(str(args.config).strip())
    if not config_path.is_absolute():
        config_path = repo_root / config_path
    if not config_path.is_file():
        print(f"error: config not found: {config_path}", file=sys.stderr)
        return 2

    report_raw = str(args.report).strip()
    if report_raw:
        report_path = Path(report_raw)
        if not report_path.is_absolute():
            report_path = repo_root / report_path
    else:
        report_path = repo_root / "tmp" / f"repl-regression-{agent_id}.json"

    proactive_wait = float(args.proactive_wait_sec)
    if proactive_wait < 0:
        print("error: --proactive-wait-sec must be >= 0", file=sys.stderr)
        return 2

    return run_regression(
        repo_root=repo_root,
        agent_id=agent_id,
        api_base=str(args.api_base).strip(),
        config_path=config_path,
        user_id=str(args.user_id).strip(),
        bootstrap_turns=_DEFAULT_BOOTSTRAP_TURNS,
        bootstrap_finish_turn=_DEFAULT_BOOTSTRAP_FINISH_TURN,
        settled_turn=_DEFAULT_SETTLED_TURN,
        proactive_wait_sec=proactive_wait,
        report_path=report_path,
        token_path=str(args.token_file).strip(),
        strict=bool(args.strict),
        stderr=sys.stderr,
    )


if __name__ == "__main__":
    raise SystemExit(main())
