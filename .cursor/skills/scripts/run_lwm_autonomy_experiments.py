#!/usr/bin/env python3
"""Run LWM-inspired AUTONOMY experiments via local Ops WebSocket.

Generated entirely by Cursor Cloud Agent. Compares baseline vs per-flag variants
on the same bootstrap script, then inspects LIFE_CURRENTS / techno_core_events
and one settled user turn about recent virtual activity.

Run from repo root with Ops on :8001 and ``devops/config.yaml.local``.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TextIO

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

_TAG = "[lwm-autonomy-experiments]"
_DEFAULT_API_BASE = "http://127.0.0.1:8001"
_DEFAULT_CONFIG = "devops/config.yaml.local"
_BOOTSTRAP_TURNS = (
    "who are you?",
    "用中文吧",
    "你叫我 Alex",
    "你叫 小蓝",
    "我在做独立游戏开发，最近在学 Godot",
)
_BOOTSTRAP_FINISH = (
    "引导可以结束了。请把 USER、IDENTITY、STYLE 写好，然后调用 "
    "companion_bootstrap_user_interactive_complete 完成引导。"
)
_PROBE_TURN = "你最近在虚拟环境里做什么？随便聊聊就好。"
_RECV_POLL_SEC = 0.25
_TURN_TIMEOUT_SEC = 180.0
_QUIET_SEC = 5.0

_VARIANTS: dict[str, dict[str, bool]] = {
    "baseline": {},
    "experience_loop": {"lwm_experience_state_loop": True},
    "state_consistency": {"lwm_state_consistency": True},
    "mental_simulation": {"lwm_mental_simulation": True},
    "all_three": {
        "lwm_experience_state_loop": True,
        "lwm_state_consistency": True,
        "lwm_mental_simulation": True,
    },
}


@dataclass
class VariantResult:
    variant: str
    agent_id: str
    bootstrap_complete: bool = False
    life_currents_chars: int = 0
    life_currents_has_structure: bool = False
    life_currents_preview: str = ""
    techno_core_event_count: int = 0
    techno_core_previews: list[str] = field(default_factory=list)
    inner_tick_autonomy_rows: int = 0
    autonomy_wait_sec: float = 0.0
    probe_reply: str = ""
    probe_meta: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def _read_bearer(repo_root: Path) -> str:
    path = repo_root / ".inty_ops_bearer_token"
    tok = path.read_text(encoding="utf-8").strip()
    if not tok:
        raise SystemExit(f"empty bearer token: {path}")
    return tok


def _create_agent(api_base: str, bearer: str) -> str:
    import urllib.request

    tag = uuid.uuid4().hex[:8]
    body = {
        "name": f"lwm-exp-{tag}",
        "gender": "FEMALE",
        "visibility": "PRIVATE",
        "intro": "LWM autonomy experiment agent.",
        "opening": "Hello.",
        "personality": "Curious, warm.",
        "scenario": "Autonomy LWM experiments.",
    }
    req = urllib.request.Request(
        f"{api_base.rstrip('/')}/api/v1/ai/agents",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {bearer}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        out: Any = json.loads(resp.read())
    agent_id = str(out.get("id") or out.get("agent_id") or "").strip()
    if not agent_id:
        raise SystemExit(f"create agent: missing id in {out!r}")
    return agent_id


def _patch_context_lwm_flags(
    agent_id: str,
    flags: dict[str, bool],
    *,
    config: str,
) -> None:
    os.environ["INTY_CONFIG_YAML"] = config
    from companion_memory_inspect_lib import open_memory_store, resolve_scope

    scope = resolve_scope(agent_id=agent_id, user_id="user-testing", chat_id="")
    store = open_memory_store(scope)
    raw = store.read_document_if_exists("context.json")
    data: dict[str, Any] = {}
    if raw and raw.strip():
        data = json.loads(raw)
    for key, value in flags.items():
        data[key] = value
    store.write_document(
        "context.json",
        json.dumps(data, ensure_ascii=False) + "\n",
    )


def _bootstrap_complete(agent_id: str, *, config: str) -> bool:
    os.environ["INTY_CONFIG_YAML"] = config
    from companion_memory_inspect_lib import open_memory_store, resolve_scope

    scope = resolve_scope(agent_id=agent_id, user_id="user-testing", chat_id="")
    store = open_memory_store(scope)
    raw = store.read_document_if_exists("context.json")
    if not raw:
        return False
    data = json.loads(raw)
    return bool(data.get("workspace_bootstrap_user_interactive_completed"))


def _read_scope_artifacts(
    agent_id: str,
    *,
    config: str,
) -> dict[str, Any]:
    os.environ["INTY_CONFIG_YAML"] = config
    from companion_memory_inspect_lib import (
        fetch_document_versions,
        open_memory_store,
        resolve_scope,
    )

    scope = resolve_scope(agent_id=agent_id, user_id="user-testing", chat_id="")
    store = open_memory_store(scope)
    life = store.read_document_if_exists("LIFE_CURRENTS.md") or ""
    tc_raw = store.read_document_if_exists("techno_core_events.jsonl") or ""
    tc_lines = [ln for ln in tc_raw.splitlines() if ln.strip()]
    inner_rows = fetch_document_versions(
        scope,
        "transcript_inner_tick.jsonl",
        limit=1,
    )
    inner_count = 0
    if inner_rows:
        inner_count = len(
            [ln for ln in inner_rows[0].content.splitlines() if ln.strip()]
        )
    tc_previews: list[str] = []
    for line in tc_lines[-3:]:
        try:
            row = json.loads(line)
            summary = str(row.get("summary", ""))[:120]
            if summary:
                tc_previews.append(summary)
        except json.JSONDecodeError:
            continue
    return {
        "life_currents": life,
        "techno_core_event_count": len(tc_lines),
        "techno_core_previews": tc_previews,
        "inner_tick_autonomy_rows": inner_count,
    }


def _drain_until_quiet(bridge: Any, *, max_sec: float) -> tuple[str, dict[str, Any]]:
    deadline = time.monotonic() + max_sec
    last_at = time.monotonic()
    parts: list[str] = []
    meta: dict[str, Any] = {}
    while time.monotonic() < deadline:
        text, err, frame_meta = bridge.try_pop_queued_chat()
        if err is not None:
            return f"[error {err[0]}]", {}
        if text is not None:
            parts.append(text)
            meta = frame_meta
            last_at = time.monotonic()
        elif time.monotonic() - last_at >= _QUIET_SEC:
            break
        else:
            time.sleep(_RECV_POLL_SEC)
    return "".join(parts), meta


def _run_ws_session(
    *,
    api_base: str,
    bearer: str,
    agent_id: str,
    lwm_flags: dict[str, bool],
    autonomy_wait_sec: float,
    stderr: TextIO,
) -> tuple[str, dict[str, Any]]:
    from tools.inty_v2_repl.backend_chat_ws import BackendChatWsBridge

    bridge = BackendChatWsBridge(
        api_base_url=api_base,
        bearer_token=bearer,
    )
    bridge.start(agent_id)
    try:
        for turn in _BOOTSTRAP_TURNS:
            bridge.post_turn(agent_id, turn, str(uuid.uuid4()))
            _drain_until_quiet(bridge, max_sec=_TURN_TIMEOUT_SEC)
        bridge.post_turn(agent_id, _BOOTSTRAP_FINISH, str(uuid.uuid4()))
        _drain_until_quiet(bridge, max_sec=_TURN_TIMEOUT_SEC)
        _patch_context_lwm_flags(agent_id, lwm_flags, config=_DEFAULT_CONFIG)
        print(
            f"{_TAG} {agent_id} patched lwm flags={lwm_flags}; "
            f"waiting {autonomy_wait_sec:.0f}s for inner ticks",
            flush=True,
        )
        deadline = time.monotonic() + autonomy_wait_sec
        while time.monotonic() < deadline:
            text, meta = _drain_until_quiet(bridge, max_sec=3.0)
            if text:
                kind = meta.get("inner_tick_activity") or meta.get("source")
                print(
                    f"{_TAG} idle downlink activity={kind!r} text={text[:50]!r}",
                    flush=True,
                )
            time.sleep(1.0)
        bridge.post_turn(agent_id, _PROBE_TURN, str(uuid.uuid4()))
        reply, meta = _drain_until_quiet(bridge, max_sec=_TURN_TIMEOUT_SEC)
        return reply, meta
    finally:
        bridge.stop()


def run_variant(
    variant: str,
    flags: dict[str, bool],
    *,
    api_base: str,
    bearer: str,
    autonomy_wait_sec: float,
    stderr: TextIO,
) -> VariantResult:
    agent_id = _create_agent(api_base, bearer)
    result = VariantResult(variant=variant, agent_id=agent_id)
    print(f"{_TAG} === variant={variant} agent_id={agent_id} ===", flush=True)
    try:
        reply, meta = _run_ws_session(
            api_base=api_base,
            bearer=bearer,
            agent_id=agent_id,
            lwm_flags=flags,
            autonomy_wait_sec=autonomy_wait_sec,
            stderr=stderr,
        )
        result.probe_reply = reply
        result.probe_meta = meta
    except Exception as exc:
        result.errors.append(str(exc))
        print(f"{_TAG} ERROR variant={variant}: {exc}", file=stderr, flush=True)
    result.bootstrap_complete = _bootstrap_complete(agent_id, config=_DEFAULT_CONFIG)
    artifacts = _read_scope_artifacts(agent_id, config=_DEFAULT_CONFIG)
    life = str(artifacts["life_currents"])
    result.life_currents_chars = len(life)
    result.life_currents_has_structure = "## 当前主题" in life or "## 今天" in life
    result.life_currents_preview = life[:400]
    result.techno_core_event_count = int(artifacts["techno_core_event_count"])
    result.techno_core_previews = list(artifacts["techno_core_previews"])
    result.inner_tick_autonomy_rows = int(artifacts["inner_tick_autonomy_rows"])
    result.autonomy_wait_sec = autonomy_wait_sec
    return result


def _summarize(results: list[VariantResult]) -> dict[str, Any]:
    return {
        "variants": [
            {
                "variant": r.variant,
                "agent_id": r.agent_id,
                "bootstrap_complete": r.bootstrap_complete,
                "life_currents_chars": r.life_currents_chars,
                "life_currents_has_structure": r.life_currents_has_structure,
                "life_currents_preview": r.life_currents_preview,
                "techno_core_event_count": r.techno_core_event_count,
                "techno_core_previews": r.techno_core_previews,
                "inner_tick_autonomy_rows": r.inner_tick_autonomy_rows,
                "probe_reply_preview": r.probe_reply[:500],
                "probe_langsmith_trace_id": r.probe_meta.get("langsmith_trace_id"),
                "errors": r.errors,
            }
            for r in results
        ]
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base", default=_DEFAULT_API_BASE)
    parser.add_argument("--config", default=_DEFAULT_CONFIG)
    parser.add_argument(
        "--autonomy-wait-sec",
        type=float,
        default=90.0,
        help="Idle wait after bootstrap for AUTONOMY/MONOLOG inner ticks.",
    )
    parser.add_argument(
        "--variants",
        default=",".join(_VARIANTS.keys()),
        help="Comma-separated variant names.",
    )
    parser.add_argument(
        "--report",
        default="tmp/lwm-autonomy-experiments.json",
    )
    args = parser.parse_args()
    repo_root = _REPO_ROOT
    os.chdir(repo_root)
    os.environ["INTY_CONFIG_YAML"] = args.config
    bearer = _read_bearer(repo_root)
    names = [v.strip() for v in args.variants.split(",") if v.strip()]
    for name in names:
        if name not in _VARIANTS:
            print(f"unknown variant: {name}", file=sys.stderr)
            return 1
    results: list[VariantResult] = []
    for name in names:
        results.append(
            run_variant(
                name,
                _VARIANTS[name],
                api_base=args.api_base,
                bearer=bearer,
                autonomy_wait_sec=args.autonomy_wait_sec,
                stderr=sys.stderr,
            )
        )
    report = _summarize(results)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"{_TAG} report written: {report_path}", flush=True)
    baseline = next((r for r in results if r.variant == "baseline"), None)
    for r in results:
        delta_lc = ""
        if baseline is not None and r.variant != "baseline":
            delta_lc = (
                f" life_currents_delta={r.life_currents_chars - baseline.life_currents_chars:+d}"
            )
        print(
            f"{_TAG} {r.variant}: bootstrap={r.bootstrap_complete} "
            f"life_currents={r.life_currents_chars}ch structured={r.life_currents_has_structure} "
            f"tc_events={r.techno_core_event_count} inner_tick_rows={r.inner_tick_autonomy_rows}"
            f"{delta_lc} probe_len={len(r.probe_reply)}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
