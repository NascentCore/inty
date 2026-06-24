#!/usr/bin/env python3
"""Automated local Ops + WebSocket regression for companion queue-serving.

Skill smoke driver (not ``app/`` production code). Drives implicit sign-on greeting,
bootstrap turns (MemoryDoc checks), ``companion_set_experience_profile``, one settled
user turn, a GitHub issue complaint turn, inner-tick proactive chat rounds, and scope-worker
dreaming consolidation (``MEMORY.md`` update) via ``BackendChatWsBridge`` (same transport
as ``inty_v2_repl``). Writes a JSON report under ``tmp/`` and prints a one-line SUMMARY.

Layout:
- Driver: ``run_regression`` / ``main`` for end-to-end WS and Postgres checks.
- Greeting: require WS downlink with ``meta_data.source=greeting`` after connect.
- Bootstrap MemDocs: USER/IDENTITY/STYLE customized; SOUL/MEMORY remain template seed.
- Experience profile: ``companion_set_experience_profile`` → ``context_mode=roleplay``.
- Settled turn: wait for InputQueue idle after bootstrap-finish, match WS
  ``user_msg_uuid`` to the sent turn, wait for InputQueue ``delivered``, then
  run github_issue E2E phase, then start proactive multi-round wait, then poll dreaming.
- Proactive: collect WS downlinks and merge ``chat_history`` synthetic user rows;
  require ``--proactive-min-rounds`` (default 1) with ``--proactive-target-rounds`` (default 2,
  summary-only); fast local idle (10s + poll 3s); fail on legacy ``[SILENT]`` token in previews.
- Dreaming: poll ``.companion_dreaming_state.json`` + ``MEMORY.md`` sequence after proactive
  (``dreaming_idle_seconds=10`` in ``devops/config.yaml.local``; ``--dreaming-wait-sec`` default 90).
- GitHub issue: USER_CHAT complaint → poll ``companion_user_feedback_jsonl`` →
  ``gh issue view`` → ``gh issue close`` cleanup.
- Strict-mode DB verification: below ``_is_inner_tick_proactive``; when no
  proactive WS frame arrives, it queries ``chat_history`` for silent inner ticks.
  ``_parse_proactive_chat_history_rows`` and feedback JSONL parsers are unit-tested in
  ``tests/cursor/skills/scripts/test_run_inty_repl_regression.py``.

Run with shell cwd = repository root (or any path under the repo).

TODO(#3606): Split mandatory pass gate (infra-only) from live LLM eval smoke;
github_issue_e2e and proactive target rounds should not block exit 0.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import shutil
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
_DEFAULT_GITHUB_ISSUE_TURN = (
    "我很不满——你刚才的回答没有考虑我在美国西海岸的时区。"
    "请先用 companion_record_user_feedback 把我的投诉提交成 GitHub issue，再简短回复我。"
)
_DEFAULT_EXPERIENCE_PROFILE_TURN = (
    "【系统回归】你必须先调用 companion_set_experience_profile("
    'experience_intent="roleplay", note="regression")，'
    "成功后再用一句话确认已切换到角色扮演模式。不要写 MemDoc 代替该 tool。"
)
_DEFAULT_EXPERIENCE_PROFILE_CONTEXT_MODE = "roleplay"
_BOOTSTRAP_USER_NAME_MARKER = "大雄"
_BOOTSTRAP_COMPANION_NAME_MARKER = "多啦"
_DEFAULT_DREAMING_WAIT_SEC = 900.0
_DREAMING_POLL_SEC = 3.0
_EXPERIENCE_PROFILE_POLL_SEC = 2.0
_EXPERIENCE_PROFILE_POLL_TIMEOUT_SEC = 120.0
_GITHUB_ISSUE_POLL_SEC = 60.0
_RECV_POLL_SEC = 0.25
_INPUT_QUEUE_POLL_SEC = 0.5
_TURN_REPLY_TIMEOUT_SEC = 180.0
_TURN_TRAILING_QUIET_SEC = 5.0
_BOOTSTRAP_TURN_SETTLE_QUIET_SEC = 20.0
_BOOTSTRAP_TURN_SETTLE_MAX_SEC = 300.0
_PRE_SETTLED_WS_DRAIN_QUIET_SEC = 3.0
# Match devops/config.yaml.local fast proactive: idle 10s + poll 3s + LLM slack.
# ``--proactive-wait-sec``: wall-clock listen duration (not capped by min/target rounds).
# ``--proactive-min-rounds``: pass gate (default 1; silent-first round cannot schedule a 2nd).
# ``--proactive-target-rounds``: stretch goal logged in summary; does not fail the run.
_DEFAULT_PROACTIVE_MIN_ROUNDS = 1
_DEFAULT_PROACTIVE_TARGET_ROUNDS = 2
_DEFAULT_PROACTIVE_WAIT_SEC = 120.0
_PROACTIVE_LEGACY_SILENT_TOKEN = "[SILENT]"
_PROACTIVE_RECV_CHUNK_SEC = 5.0
_POST_PROACTIVE_DRAIN_QUIET_SEC = 5.0
_POST_PROACTIVE_DRAIN_MAX_SEC = 20.0


@dataclass(frozen=True)
class ProactiveChatHistoryRow:
    """Synthetic proactive user row observed in ``chat_history`` after the run starts."""

    chat_history_id: str
    content_preview: str
    created_at: str
    has_assistant_reply: bool


@dataclass(frozen=True)
class FeedbackGithubIssueRow:
    """Parsed ``kind=github_issue_created`` line from agent-scope feedback JSONL."""

    issue_url: str
    issue_number: int
    user_msg_uuid: str
    feedback_id: str


@dataclass(frozen=True)
class GithubIssueE2eResult:
    """Outcome of the github_issue regression phase for JSON report + pass bit."""

    user_msg_uuid: str
    issue_url: str
    issue_number: int
    snapshot_seen: bool
    closed: bool
    disclosed_in_chat: bool
    error: str | None


@dataclass(frozen=True)
class ImplicitSignOnGreetingResult:
    """Outcome of implicit sign-on greeting verification."""

    present: bool
    source_greeting: bool
    text_preview: str
    langsmith_trace_id: str


@dataclass(frozen=True)
class BootstrapMemDocResult:
    """Post-bootstrap MemoryStore document checks."""

    user_customized: bool
    identity_customized: bool
    style_customized: bool
    soul_unchanged: bool
    memory_unchanged: bool
    user_sequence_id: int
    identity_sequence_id: int
    style_sequence_id: int
    memory_sequence_id: int
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class DreamingConsolidationResult:
    """Dreaming batch checkpoint + MEMORY.md update checks."""

    checkpoint_present: bool
    memory_updated: bool
    memory_sequence_before: int
    memory_sequence_after: int
    error: str | None


@dataclass(frozen=True)
class MemDocVersion:
    """One latest MemoryStore document version row."""

    sequence_id: int
    content: str


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
) -> str:
    """Drain interim OutputQueue WS frames until the turn is quiet (multi-round tool loop)."""
    trailing = _drain_until_quiet(
        bridge,
        quiet_sec=_TURN_TRAILING_QUIET_SEC,
        max_sec=_TURN_REPLY_TIMEOUT_SEC,
    )
    parts: list[str] = []
    for text, meta in trailing:
        parts.append(text)
        _record_trailing_downlink(report, label=label, text=text, meta=meta)
    return "".join(parts)


def _wait_ws_turn_settled(
    bridge: Any,
    report: dict[str, Any],
    *,
    label: str,
    settle_quiet_sec: float,
    max_sec: float,
    stderr: TextIO,
) -> bool:
    """Keep draining WS downlinks until a multi-round tool turn is fully quiet."""
    assert settle_quiet_sec > 0.0
    assert max_sec > 0.0
    deadline = time.monotonic() + max_sec
    last_frame_at = time.monotonic()
    while time.monotonic() < deadline:
        drained = _drain_until_quiet(
            bridge,
            quiet_sec=2.0,
            max_sec=min(15.0, max(0.0, deadline - time.monotonic())),
        )
        if drained:
            for text, meta in drained:
                _record_trailing_downlink(
                    report, label=label, text=text, meta=meta
                )
            last_frame_at = time.monotonic()
        elif time.monotonic() - last_frame_at >= settle_quiet_sec:
            print(
                f"{_TAG} ws turn settled ({label}) quiet={settle_quiet_sec}s",
                flush=True,
            )
            return True
        else:
            time.sleep(_RECV_POLL_SEC)
    print(
        f"{_TAG} ERROR timeout waiting for ws turn settle ({label}) "
        f"max_sec={max_sec}",
        file=stderr,
        flush=True,
    )
    return False


def _send_turn(bridge: Any, agent_id: str, text: str) -> str:
    msg_uuid = str(uuid.uuid4())
    bridge.post_turn(agent_id, text, msg_uuid)
    return msg_uuid


def _parse_input_queue_status_counts(raw: str) -> dict[str, int]:
    """Parse ``status|count`` lines from InputQueue GROUP BY query."""
    counts: dict[str, int] = {}
    for line in raw.strip().splitlines():
        if not line.strip():
            continue
        status, count_s = line.split("|", 1)
        counts[status] = int(count_s)
    return counts


def _input_queue_has_in_flight(counts: dict[str, int]) -> bool:
    """True when any InputQueue row is still pending or claimed."""
    return counts.get("pending", 0) > 0 or counts.get("claimed", 0) > 0


def _output_queue_has_in_flight(counts: dict[str, int]) -> bool:
    """True when any OutputQueue row is still pending or claimed."""
    return counts.get("pending", 0) > 0 or counts.get("claimed", 0) > 0


def _query_output_queue_status_counts(
    repo_root: Path,
    config_path: Path,
    *,
    agent_id: str,
) -> dict[str, int]:
    assert agent_id != ""
    raw = _psql(
        repo_root,
        config_path,
        "SELECT status, COUNT(*) FROM agentic_companion_output_queue "
        f"WHERE agent_id = '{agent_id}' GROUP BY status ORDER BY status;",
    )
    return _parse_input_queue_status_counts(raw)


def _wait_output_queue_idle(
    repo_root: Path,
    config_path: Path,
    *,
    agent_id: str,
    timeout_sec: float,
    label: str,
    stderr: TextIO,
) -> bool:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        counts = _query_output_queue_status_counts(
            repo_root, config_path, agent_id=agent_id
        )
        if not _output_queue_has_in_flight(counts):
            print(
                f"{_TAG} output queue idle ({label}) counts={counts}",
                flush=True,
            )
            return True
        time.sleep(_INPUT_QUEUE_POLL_SEC)
    counts = _query_output_queue_status_counts(
        repo_root, config_path, agent_id=agent_id
    )
    print(
        f"{_TAG} ERROR timeout waiting for output queue idle ({label}) "
        f"counts={counts}",
        file=stderr,
        flush=True,
    )
    return False


def _query_input_queue_status_counts(
    repo_root: Path,
    config_path: Path,
    *,
    agent_id: str,
) -> dict[str, int]:
    assert agent_id != ""
    raw = _psql(
        repo_root,
        config_path,
        "SELECT status, COUNT(*) FROM agentic_companion_input_queue "
        f"WHERE agent_id = '{agent_id}' GROUP BY status ORDER BY status;",
    )
    return _parse_input_queue_status_counts(raw)


def _query_input_status_for_client_message_id(
    repo_root: Path,
    config_path: Path,
    *,
    agent_id: str,
    client_message_id: str,
) -> str:
    assert agent_id != ""
    assert client_message_id != ""
    return _psql(
        repo_root,
        config_path,
        "SELECT status FROM agentic_companion_input_queue "
        f"WHERE agent_id = '{agent_id}' "
        f"AND client_message_id = '{client_message_id}' "
        "ORDER BY sequence_id DESC LIMIT 1;",
    ).strip()


def _wait_input_queue_idle(
    repo_root: Path,
    config_path: Path,
    *,
    agent_id: str,
    timeout_sec: float,
    label: str,
    stderr: TextIO,
) -> bool:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        counts = _query_input_queue_status_counts(
            repo_root, config_path, agent_id=agent_id
        )
        if not _input_queue_has_in_flight(counts):
            print(
                f"{_TAG} input queue idle ({label}) counts={counts}",
                flush=True,
            )
            return True
        time.sleep(_INPUT_QUEUE_POLL_SEC)
    counts = _query_input_queue_status_counts(
        repo_root, config_path, agent_id=agent_id
    )
    print(
        f"{_TAG} ERROR timeout waiting for input queue idle ({label}) "
        f"counts={counts}",
        file=stderr,
        flush=True,
    )
    return False


def _wait_input_delivered(
    repo_root: Path,
    config_path: Path,
    *,
    agent_id: str,
    client_message_id: str,
    timeout_sec: float,
    label: str,
    stderr: TextIO,
) -> bool:
    assert client_message_id != ""
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        status = _query_input_status_for_client_message_id(
            repo_root,
            config_path,
            agent_id=agent_id,
            client_message_id=client_message_id,
        )
        match status:
            case "delivered":
                print(
                    f"{_TAG} input delivered ({label}) "
                    f"client_message_id={client_message_id}",
                    flush=True,
                )
                return True
            case "failed":
                print(
                    f"{_TAG} ERROR input failed ({label}) "
                    f"client_message_id={client_message_id}",
                    file=stderr,
                    flush=True,
                )
                return False
            case _:
                time.sleep(_INPUT_QUEUE_POLL_SEC)
    print(
        f"{_TAG} ERROR timeout waiting for input delivered ({label}) "
        f"client_message_id={client_message_id} last_status={status!r}",
        file=stderr,
        flush=True,
    )
    return False


def _downlink_user_msg_uuid(meta: dict[str, Any]) -> str:
    return str(meta.get("user_msg_uuid") or "").strip()


def _wait_downlink_for_user_msg_uuid(
    bridge: Any,
    report: dict[str, Any],
    *,
    expected_user_msg_uuid: str,
    timeout_sec: float,
    label: str,
    trailing_label: str,
) -> tuple[str | None, dict[str, Any], tuple[int, str] | None]:
    """Accept only a WS downlink whose ``user_msg_uuid`` matches the sent turn."""
    assert expected_user_msg_uuid != ""
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        text, err, meta = bridge.try_pop_queued_chat()
        if err is not None:
            return None, {}, err
        if text is None:
            time.sleep(_RECV_POLL_SEC)
            continue
        actual = _downlink_user_msg_uuid(meta)
        if actual == expected_user_msg_uuid:
            return text, meta, None
        _record_trailing_downlink(
            report,
            label=trailing_label,
            text=text,
            meta=meta,
        )
        print(
            f"{_TAG} skip downlink for {label}: user_msg_uuid={actual!r} "
            f"expected={expected_user_msg_uuid!r}",
            flush=True,
        )
    return (
        None,
        {},
        (408, f"timeout waiting for {label} user_msg_uuid={expected_user_msg_uuid}"),
    )


def _load_app_debug_from_config(config_path: Path) -> bool:
    """Return ``app.debug`` from the regression config yaml (same source as Ops)."""
    import yaml

    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    app = cfg.get("app") or {}
    return bool(app.get("debug"))


def _assistant_reply_discloses_issue_url(
    reply_text: str,
    issue_url: str,
    issue_number: int,
) -> bool:
    """True when user-visible chat text includes the issue URL or ``issues/{N}`` marker."""
    if not reply_text.strip() or issue_number <= 0:
        return False
    if issue_url.strip() and issue_url in reply_text:
        return True
    return f"issues/{issue_number}" in reply_text


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


def _deactivate_active_companion_bonds_for_user(
    repo_root: Path,
    config_path: Path,
    *,
    user_id: str,
) -> int:
    """Mark ACTIVE companion bonds INACTIVE for one user before --create-agent."""
    assert user_id != ""
    raw = _psql(
        repo_root,
        config_path,
        f"""
UPDATE companion_bonds
SET state = 'INACTIVE',
    inactive_at = NOW()
WHERE user_id = '{user_id}'
  AND state = 'ACTIVE';
SELECT COUNT(*) FROM companion_bonds
WHERE user_id = '{user_id}' AND state = 'ACTIVE';
""",
    )
    lines = [line.strip() for line in raw.strip().splitlines() if line.strip()]
    remaining = int(lines[-1]) if lines else 0
    return remaining


def _query_active_companion_bond_agent_id(
    repo_root: Path,
    config_path: Path,
    *,
    user_id: str,
    agent_id: str,
) -> str | None:
    """Return ACTIVE bond state for user+agent, or None when no row."""
    assert user_id != ""
    assert agent_id != ""
    raw = _psql(
        repo_root,
        config_path,
        f"""
SELECT state FROM companion_bonds
WHERE user_id = '{user_id}'
  AND agent_id = '{agent_id}'
  AND state = 'ACTIVE'
ORDER BY created_at DESC, id DESC
LIMIT 1;
""",
    )
    line = raw.strip()
    return line if line else None


def _agent_scope_chat_id(user_id: str, agent_id: str) -> str:
    assert user_id != ""
    assert agent_id != ""
    return f"agent-scope:{user_id}:{agent_id}"


def _is_implicit_sign_on_greeting(meta: dict[str, Any]) -> bool:
    source = str(meta.get("source") or "").strip()
    if source == "greeting":
        return True
    if meta.get("isOpening") is True:
        return True
    return False


def _wait_implicit_sign_on_greeting(
    bridge: Any,
    *,
    timeout_sec: float,
) -> tuple[str | None, dict[str, Any], tuple[int, str] | None]:
    """Block until the implicit ``user_signed_on`` greeting downlink or timeout."""
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        text, err, meta = bridge.try_pop_queued_chat()
        if err is not None:
            return None, {}, err
        if text is not None:
            return text, meta, None
        time.sleep(_RECV_POLL_SEC)
    return None, {}, (408, "timeout waiting for implicit sign-on greeting")


def _verify_implicit_sign_on_greeting(
    greeting_turns: list[dict[str, Any]],
) -> ImplicitSignOnGreetingResult:
    """Require at least one non-empty WS downlink with ``meta_data.source=greeting``."""
    for turn in greeting_turns:
        text = str(turn.get("text_preview") or "").strip()
        meta = turn.get("meta") or {}
        if not text:
            continue
        if _is_implicit_sign_on_greeting(meta):
            return ImplicitSignOnGreetingResult(
                present=True,
                source_greeting=True,
                text_preview=text[:120],
                langsmith_trace_id=str(meta.get("langsmith_trace_id") or ""),
            )
    preview = ""
    if greeting_turns:
        preview = str(greeting_turns[0].get("text_preview") or "")[:120]
    return ImplicitSignOnGreetingResult(
        present=False,
        source_greeting=False,
        text_preview=preview,
        langsmith_trace_id="",
    )


def _query_latest_memdoc_version(
    repo_root: Path,
    config_path: Path,
    *,
    user_id: str,
    agent_id: str,
    document_kind: str,
) -> MemDocVersion | None:
    assert user_id != ""
    assert agent_id != ""
    assert document_kind != ""
    scope_chat = _agent_scope_chat_id(user_id, agent_id)
    raw = _psql(
        repo_root,
        config_path,
        f"""
SELECT sequence_id, trim(content)
FROM companion_memory_document_versions
WHERE companion_id = '{agent_id}'
  AND user_id = '{user_id}'
  AND chat_id = '{scope_chat}'
  AND document_kind = '{document_kind}'
  AND calendar_date IS NULL
ORDER BY sequence_id DESC
LIMIT 1;
""",
    )
    line = raw.strip()
    if not line:
        return None
    sequence_s, content = line.split("|", 1)
    return MemDocVersion(sequence_id=int(sequence_s), content=content)


def _query_context_mode(
    repo_root: Path,
    config_path: Path,
    *,
    user_id: str,
    agent_id: str,
) -> str:
    assert user_id != ""
    assert agent_id != ""
    scope_chat = _agent_scope_chat_id(user_id, agent_id)
    raw = _psql(
        repo_root,
        config_path,
        f"""
SELECT trim(content)::json->>'context_mode'
FROM companion_memory_document_versions
WHERE companion_id = '{agent_id}'
  AND user_id = '{user_id}'
  AND chat_id = '{scope_chat}'
  AND document_kind = 'context_json'
  AND calendar_date IS NULL
ORDER BY sequence_id DESC
LIMIT 1;
""",
    )
    return raw.strip()


def _poll_context_mode(
    repo_root: Path,
    config_path: Path,
    *,
    user_id: str,
    agent_id: str,
    expected: str,
    timeout_sec: float,
    bridge: Any | None,
    stderr: TextIO,
) -> bool:
    assert expected != ""
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if bridge is not None:
            for _ in range(4):
                text, err, meta = bridge.try_pop_queued_chat()
                if err is not None or text is None:
                    break
                print(
                    f"{_TAG} experience_profile poll drain text={text[:60]!r} "
                    f"source={meta.get('source')!r}",
                    flush=True,
                )
        mode = _query_context_mode(
            repo_root, config_path, user_id=user_id, agent_id=agent_id
        )
        if mode == expected:
            print(
                f"{_TAG} context_mode={mode!r} matched expected",
                flush=True,
            )
            return True
        time.sleep(_EXPERIENCE_PROFILE_POLL_SEC)
    print(
        f"{_TAG} ERROR timeout waiting for context_mode={expected!r} "
        f"(last={_query_context_mode(repo_root, config_path, user_id=user_id, agent_id=agent_id)!r})",
        file=stderr,
        flush=True,
    )
    return False


def _verify_bootstrap_memdocs(
    repo_root: Path,
    config_path: Path,
    *,
    user_id: str,
    agent_id: str,
) -> BootstrapMemDocResult:
    """Check bootstrap wrote USER/IDENTITY/STYLE while SOUL/MEMORY stay at template seed."""
    _ensure_import_path(repo_root)
    from app.core.companion_harness.memory.memory_store_scope import (
        load_template_seed_text,
    )

    soul_seed = load_template_seed_text("SOUL.md").strip()
    memory_seed = load_template_seed_text("MEMORY.md").strip()
    style_seed = load_template_seed_text("STYLE.md").strip()
    errors: list[str] = []

    user_doc = _query_latest_memdoc_version(
        repo_root,
        config_path,
        user_id=user_id,
        agent_id=agent_id,
        document_kind="user",
    )
    identity_doc = _query_latest_memdoc_version(
        repo_root,
        config_path,
        user_id=user_id,
        agent_id=agent_id,
        document_kind="identity",
    )
    style_doc = _query_latest_memdoc_version(
        repo_root,
        config_path,
        user_id=user_id,
        agent_id=agent_id,
        document_kind="style",
    )
    soul_doc = _query_latest_memdoc_version(
        repo_root,
        config_path,
        user_id=user_id,
        agent_id=agent_id,
        document_kind="soul",
    )
    memory_doc = _query_latest_memdoc_version(
        repo_root,
        config_path,
        user_id=user_id,
        agent_id=agent_id,
        document_kind="memory",
    )

    user_customized = (
        user_doc is not None
        and _BOOTSTRAP_USER_NAME_MARKER in user_doc.content
    )
    identity_customized = (
        identity_doc is not None
        and _BOOTSTRAP_COMPANION_NAME_MARKER in identity_doc.content
    )
    style_customized = (
        style_doc is not None and style_doc.content.strip() != style_seed
    )
    soul_unchanged = (
        soul_doc is not None and soul_doc.content.strip() == soul_seed
    )
    memory_unchanged = (
        memory_doc is not None and memory_doc.content.strip() == memory_seed
    )

    if user_doc is None:
        errors.append("USER.md missing")
    elif not user_customized:
        errors.append(f"USER.md missing {_BOOTSTRAP_USER_NAME_MARKER!r}")
    if identity_doc is None:
        errors.append("IDENTITY.md missing")
    elif not identity_customized:
        errors.append(f"IDENTITY.md missing {_BOOTSTRAP_COMPANION_NAME_MARKER!r}")
    if style_doc is None:
        errors.append("STYLE.md missing")
    elif not style_customized:
        errors.append("STYLE.md still template seed")
    warnings: list[str] = []
    if soul_doc is None:
        warnings.append("SOUL.md missing")
    elif not soul_unchanged:
        warnings.append("SOUL.md drifted from template seed")
    if memory_doc is None:
        warnings.append("MEMORY.md missing")
    elif not memory_unchanged:
        warnings.append("MEMORY.md drifted from template seed before dreaming")

    return BootstrapMemDocResult(
        user_customized=user_customized,
        identity_customized=identity_customized,
        style_customized=style_customized,
        soul_unchanged=soul_unchanged,
        memory_unchanged=memory_unchanged,
        user_sequence_id=user_doc.sequence_id if user_doc else 0,
        identity_sequence_id=identity_doc.sequence_id if identity_doc else 0,
        style_sequence_id=style_doc.sequence_id if style_doc else 0,
        memory_sequence_id=memory_doc.sequence_id if memory_doc else 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def _dreaming_checkpoint_present(
    repo_root: Path,
    config_path: Path,
    *,
    user_id: str,
    agent_id: str,
) -> bool:
    doc = _query_latest_memdoc_version(
        repo_root,
        config_path,
        user_id=user_id,
        agent_id=agent_id,
        document_kind="companion_dreaming_state_json",
    )
    return doc is not None and bool(doc.content.strip())


def _wait_dreaming_consolidation(
    repo_root: Path,
    config_path: Path,
    *,
    user_id: str,
    agent_id: str,
    memory_sequence_before: int,
    wait_sec: float,
    stderr: TextIO,
) -> DreamingConsolidationResult:
    """Poll until scope dreaming checkpoint exists and MEMORY.md advances."""
    assert wait_sec >= 0.0
    _ensure_import_path(repo_root)
    from app.core.companion_harness.memory.memory_store_scope import (
        load_template_seed_text,
    )

    memory_seed = load_template_seed_text("MEMORY.md").strip()
    deadline = time.monotonic() + wait_sec
    last_memory_seq = memory_sequence_before
    while time.monotonic() < deadline:
        checkpoint = _dreaming_checkpoint_present(
            repo_root, config_path, user_id=user_id, agent_id=agent_id
        )
        memory_doc = _query_latest_memdoc_version(
            repo_root,
            config_path,
            user_id=user_id,
            agent_id=agent_id,
            document_kind="memory",
        )
        memory_seq = memory_doc.sequence_id if memory_doc else 0
        last_memory_seq = memory_seq
        memory_updated = memory_doc is not None and (
            memory_seq > memory_sequence_before
            or memory_doc.content.strip() != memory_seed
        )
        if checkpoint and memory_updated:
            print(
                f"{_TAG} dreaming consolidation observed "
                f"memory_sequence={memory_seq} checkpoint=true",
                flush=True,
            )
            return DreamingConsolidationResult(
                checkpoint_present=True,
                memory_updated=True,
                memory_sequence_before=memory_sequence_before,
                memory_sequence_after=memory_seq,
                error=None,
            )
        time.sleep(_DREAMING_POLL_SEC)
    checkpoint_present = _dreaming_checkpoint_present(
        repo_root, config_path, user_id=user_id, agent_id=agent_id
    )
    memory_updated = last_memory_seq > memory_sequence_before
    return DreamingConsolidationResult(
        checkpoint_present=checkpoint_present,
        memory_updated=memory_updated,
        memory_sequence_before=memory_sequence_before,
        memory_sequence_after=last_memory_seq,
        error=(
            f"no dreaming checkpoint within {wait_sec}s "
            f"(checkpoint={checkpoint_present}, memory_updated={memory_updated}, "
            f"memory_sequence_before={memory_sequence_before}, "
            f"memory_sequence_after={last_memory_seq})"
        ),
    )


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


# --- proactive DB verification (unit-tested; see tests/cursor/skills/scripts/) ---


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


def _proactive_entry_text(entry: dict[str, Any]) -> str:
    return str(entry.get("text_preview") or "")


def _proactive_entry_has_silent_token(entry: dict[str, Any]) -> bool:
    return _PROACTIVE_LEGACY_SILENT_TOKEN in _proactive_entry_text(entry)


def _proactive_db_chat_history_id(entry: dict[str, Any]) -> str:
    meta = entry.get("meta")
    if not isinstance(meta, dict):
        return ""
    if meta.get("source") != "db_chat_history":
        return ""
    return str(meta.get("chat_history_id") or "")


def _summarize_proactive_rounds(
    entries: list[dict[str, Any]],
) -> dict[str, int]:
    visible = sum(1 for entry in entries if not entry.get("silent"))
    silent = sum(1 for entry in entries if entry.get("silent"))
    leaks = sum(1 for entry in entries if _proactive_entry_has_silent_token(entry))
    return {
        "total": len(entries),
        "visible": visible,
        "silent": silent,
        "silent_token_leaks": leaks,
    }


def _append_proactive_db_row(
    report: dict[str, Any],
    row: ProactiveChatHistoryRow,
) -> None:
    existing_ids = {
        _proactive_db_chat_history_id(entry)
        for entry in report["proactive"]
        if _proactive_db_chat_history_id(entry)
    }
    if row.chat_history_id in existing_ids:
        return
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


def _record_proactive_from_db(
    report: dict[str, Any],
    rows: list[ProactiveChatHistoryRow],
) -> None:
    for row in rows:
        _append_proactive_db_row(report, row)


def _finalize_proactive_report(
    report: dict[str, Any],
    *,
    repo_root: Path,
    config_path: Path,
    user_id: str,
    agent_id: str,
    run_started_at_utc: str,
    proactive_min_rounds: int,
    proactive_target_rounds: int,
) -> dict[str, int]:
    """Merge DB proactive rows, summarize rounds, and flag legacy ``[SILENT]`` leaks."""
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

    summary = _summarize_proactive_rounds(report["proactive"])
    report["proactive_summary"] = summary
    print(
        f"{_TAG} proactive summary total={summary['total']} "
        f"visible={summary['visible']} silent={summary['silent']} "
        f"min_rounds={proactive_min_rounds} target_rounds={proactive_target_rounds}",
        flush=True,
    )
    if summary["total"] < proactive_target_rounds:
        # TODO(#3606): Target round count is eval telemetry; do not append to
        # report["errors"] when splitting regression vs live LLM eval.
        print(
            f"{_TAG} proactive target {proactive_target_rounds} round(s) not met "
            f"(got {summary['total']}); a silent first round blocks scheduling another "
            f"until the transcript ends with an assistant reply",
            flush=True,
        )
    if summary["silent_token_leaks"]:
        report["errors"].append(
            {
                "turn": "proactive_silent_token",
                "error": (
                    500,
                    f"legacy {_PROACTIVE_LEGACY_SILENT_TOKEN!r} leaked in proactive output",
                ),
            }
        )
    if summary["total"] < proactive_min_rounds:
        report["errors"].append(
            {
                "turn": "proactive_multi_round",
                "error": (
                    500,
                    f"expected >={proactive_min_rounds} proactive rounds, "
                    f"got {summary['total']}",
                ),
            }
        )
    return summary


# --- github issue E2E (unit-tested; see tests/cursor/skills/scripts/) ---


def _require_user_feedback_github_prereqs(stderr: TextIO) -> str | None:
    """Return error message when GitHub issue regression prerequisites are missing."""
    if shutil.which("gh") is None:
        msg = "gh CLI not found on PATH"
        print(f"{_TAG} ERROR {msg}", file=stderr, flush=True)
        return msg
    from app.core.companion_harness.tools.companion_user_feedback import (
        load_user_feedback_github_config,
    )

    _repo, token = load_user_feedback_github_config()
    if not token.strip():
        msg = (
            "user_feedback_github token missing "
            "(set agent.companion_harness.user_feedback_github.token or GH_TOKEN)"
        )
        print(f"{_TAG} ERROR {msg}", file=stderr, flush=True)
        return msg
    return None


def _query_user_feedback_jsonl_content(
    repo_root: Path,
    config_path: Path,
    *,
    user_id: str,
    agent_id: str,
) -> str:
    assert user_id != ""
    assert agent_id != ""
    scope_chat = f"agent-scope:{user_id}:{agent_id}"
    return _psql(
        repo_root,
        config_path,
        f"""
SELECT content
FROM companion_memory_document_versions
WHERE companion_id = '{agent_id}'
  AND user_id = '{user_id}'
  AND chat_id = '{scope_chat}'
  AND document_kind = 'companion_user_feedback_jsonl'
  AND calendar_date IS NULL
ORDER BY sequence_id DESC
LIMIT 1;
""",
    ).strip()


def _parse_feedback_jsonl_rows(raw: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in raw.strip().split("\n"):
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def _row_user_msg_uuid(row: dict[str, Any]) -> str:
    correlation = row.get("correlation")
    if not isinstance(correlation, dict):
        return ""
    return str(correlation.get("user_msg_uuid") or "").strip()


def _find_snapshot_for_user_msg_uuid(
    rows: list[dict[str, Any]],
    user_msg_uuid: str,
) -> bool:
    assert user_msg_uuid != ""
    for row in rows:
        if row.get("kind") != "snapshot":
            continue
        if _row_user_msg_uuid(row) == user_msg_uuid:
            return True
    return False


def _find_feedback_id_for_user_msg_uuid(
    rows: list[dict[str, Any]],
    user_msg_uuid: str,
) -> str:
    assert user_msg_uuid != ""
    for row in rows:
        if row.get("kind") != "snapshot":
            continue
        if _row_user_msg_uuid(row) == user_msg_uuid:
            return str(row.get("feedback_id") or "").strip()
    return ""


def _find_github_issue_skipped_reason(
    rows: list[dict[str, Any]],
    *,
    feedback_id: str,
) -> str | None:
    assert feedback_id != ""
    for row in rows:
        if row.get("kind") != "github_issue_skipped":
            continue
        if str(row.get("feedback_id") or "").strip() != feedback_id:
            continue
        reason = str(row.get("github_issue_status") or "").strip()
        return reason if reason else "github_issue_skipped"
    return None


def _parse_feedback_github_issue_row(
    rows: list[dict[str, Any]],
    *,
    user_msg_uuid: str,
    feedback_id: str,
) -> FeedbackGithubIssueRow | None:
    assert user_msg_uuid != ""
    assert feedback_id != ""
    created: FeedbackGithubIssueRow | None = None
    for row in rows:
        if row.get("kind") != "github_issue_created":
            continue
        if str(row.get("feedback_id") or "").strip() != feedback_id:
            continue
        issue_url = str(row.get("github_issue_url") or "").strip()
        issue_number = int(row.get("github_issue_number") or 0)
        if not issue_url or issue_number <= 0:
            continue
        created = FeedbackGithubIssueRow(
            issue_url=issue_url,
            issue_number=issue_number,
            user_msg_uuid=user_msg_uuid,
            feedback_id=feedback_id,
        )
    return created


def _poll_feedback_github_issue(
    repo_root: Path,
    config_path: Path,
    *,
    user_id: str,
    agent_id: str,
    user_msg_uuid: str,
    feedback_id: str,
    timeout_sec: float,
) -> FeedbackGithubIssueRow:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        raw = _query_user_feedback_jsonl_content(
            repo_root,
            config_path,
            user_id=user_id,
            agent_id=agent_id,
        )
        rows = _parse_feedback_jsonl_rows(raw)
        skipped = _find_github_issue_skipped_reason(rows, feedback_id=feedback_id)
        if skipped is not None:
            raise RuntimeError(f"github_issue_skipped: {skipped}")
        row = _parse_feedback_github_issue_row(
            rows,
            user_msg_uuid=user_msg_uuid,
            feedback_id=feedback_id,
        )
        if row is not None:
            return row
        time.sleep(1.0)
    raise TimeoutError(
        f"no github_issue_created for feedback_id={feedback_id} within {timeout_sec}s"
    )


def _verify_github_issue_via_gh(
    row: FeedbackGithubIssueRow,
    *,
    expected_user_msg_uuid: str,
) -> None:
    from app.core.companion_harness.tools.companion_user_feedback_github_issue import (
        GITHUB_ISSUE_TITLE_PREFIX,
    )

    view = subprocess.run(
        [
            "gh",
            "issue",
            "view",
            str(row.issue_number),
            "--json",
            "title,labels,body",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if view.returncode != 0:
        raise RuntimeError(view.stderr.strip() or "gh issue view failed")
    data = json.loads(view.stdout)
    title = str(data.get("title") or "")
    labels = [lb.get("name") for lb in data.get("labels") or []]
    body = str(data.get("body") or "")
    if not title.startswith(GITHUB_ISSUE_TITLE_PREFIX):
        raise RuntimeError(f"bad issue title: {title!r}")
    if expected_user_msg_uuid not in body:
        raise RuntimeError("issue body missing user_msg_uuid correlation")
    if "agentic_companion" not in labels:
        raise RuntimeError(f"missing agentic_companion label: {labels}")
    if "user-reported" not in labels:
        raise RuntimeError(f"missing user-reported label: {labels}")
    if "bug" not in labels:
        raise RuntimeError(f"missing bug label: {labels}")


def _close_github_issue(issue_number: int) -> bool:
    assert issue_number > 0
    close = subprocess.run(
        [
            "gh",
            "issue",
            "close",
            str(issue_number),
            "--comment",
            "Closed by inty-repl-regression cleanup.",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return close.returncode == 0


def _github_issue_e2e_result_to_report(result: GithubIssueE2eResult) -> dict[str, Any]:
    return {
        "user_msg_uuid": result.user_msg_uuid,
        "issue_url": result.issue_url,
        "issue_number": result.issue_number,
        "snapshot_seen": result.snapshot_seen,
        "closed": result.closed,
        "disclosed_in_chat": result.disclosed_in_chat,
        "error": result.error,
    }


def _run_github_issue_e2e_phase(
    *,
    bridge: Any,
    report: dict[str, Any],
    repo_root: Path,
    config_path: Path,
    agent_id: str,
    user_id: str,
    turn_text: str,
    stderr: TextIO,
) -> GithubIssueE2eResult:
    user_msg_uuid = ""
    issue_url = ""
    issue_number = 0
    snapshot_seen = False
    disclosed_in_chat = False
    error: str | None = None
    closed = False
    assistant_reply = ""

    try:
        prereq_err = _require_user_feedback_github_prereqs(stderr)
        if prereq_err is not None:
            error = prereq_err
        else:
            print(f"{_TAG} github_issue turn: {turn_text!r}", flush=True)
            user_msg_uuid = _send_turn(bridge, agent_id, turn_text)
            text, meta, err = _wait_downlink_for_user_msg_uuid(
                bridge,
                report,
                expected_user_msg_uuid=user_msg_uuid,
                timeout_sec=_TURN_REPLY_TIMEOUT_SEC,
                label="github_issue",
                trailing_label="github_issue_mismatch",
            )
            if err is not None:
                error = f"ws downlink: {err}"
                print(f"{_TAG} ERROR github_issue: {err}", file=stderr, flush=True)
            else:
                assert text is not None
                report["turns"].append(
                    {
                        "kind": "github_issue",
                        "user": turn_text,
                        "user_msg_uuid": user_msg_uuid,
                        "text_preview": text[:120],
                        "meta": meta,
                    }
                )
                print(
                    f"{_TAG} github_issue reply={text[:80]!r} "
                    f"user_msg_uuid={user_msg_uuid}",
                    flush=True,
                )
                trailing_text = _drain_turn_trailing_frames(
                    bridge, report, label="github_issue"
                )
                assistant_reply = text + trailing_text

                if not _wait_input_delivered(
                    repo_root,
                    config_path,
                    agent_id=agent_id,
                    client_message_id=user_msg_uuid,
                    timeout_sec=_TURN_REPLY_TIMEOUT_SEC,
                    label="github_issue",
                    stderr=stderr,
                ):
                    error = f"input not delivered: {user_msg_uuid}"
                else:
                    raw = _query_user_feedback_jsonl_content(
                        repo_root,
                        config_path,
                        user_id=user_id,
                        agent_id=agent_id,
                    )
                    rows = _parse_feedback_jsonl_rows(raw)
                    snapshot_seen = _find_snapshot_for_user_msg_uuid(
                        rows, user_msg_uuid
                    )
                    if not snapshot_seen:
                        error = (
                            f"no feedback snapshot for user_msg_uuid={user_msg_uuid}"
                        )
                        print(f"{_TAG} ERROR {error}", file=stderr, flush=True)
                    else:
                        feedback_id = _find_feedback_id_for_user_msg_uuid(
                            rows, user_msg_uuid
                        )
                        if not feedback_id:
                            error = (
                                f"no feedback_id for user_msg_uuid={user_msg_uuid}"
                            )
                        else:
                            issue_row = _poll_feedback_github_issue(
                                repo_root,
                                config_path,
                                user_id=user_id,
                                agent_id=agent_id,
                                user_msg_uuid=user_msg_uuid,
                                feedback_id=feedback_id,
                                timeout_sec=_GITHUB_ISSUE_POLL_SEC,
                            )
                            issue_url = issue_row.issue_url
                            issue_number = issue_row.issue_number
                            _verify_github_issue_via_gh(
                                issue_row,
                                expected_user_msg_uuid=user_msg_uuid,
                            )
                            post_deliver_trailing = _drain_turn_trailing_frames(
                                bridge,
                                report,
                                label="github_issue_post_deliver",
                            )
                            assistant_reply += post_deliver_trailing
                            disclosed_in_chat = _assistant_reply_discloses_issue_url(
                                assistant_reply,
                                issue_url,
                                issue_number,
                            )
                            print(
                                f"{_TAG} github_issue verified issue=#{issue_number} "
                                f"url={issue_url} disclosed_in_chat={disclosed_in_chat}",
                                flush=True,
                            )
    except (RuntimeError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
        error = str(exc)
        print(f"{_TAG} ERROR github_issue_e2e: {error}", file=stderr, flush=True)
    finally:
        if issue_number > 0:
            closed = _close_github_issue(issue_number)
            if closed:
                print(
                    f"{_TAG} github_issue closed issue=#{issue_number}",
                    flush=True,
                )
            else:
                msg = f"gh issue close failed for #{issue_number}"
                print(f"{_TAG} ERROR {msg}", file=stderr, flush=True)
                if error is None:
                    error = msg

    return GithubIssueE2eResult(
        user_msg_uuid,
        issue_url,
        issue_number,
        snapshot_seen,
        closed,
        disclosed_in_chat,
        error,
    )


def _run_experience_profile_phase(
    *,
    bridge: Any,
    report: dict[str, Any],
    repo_root: Path,
    config_path: Path,
    agent_id: str,
    user_id: str,
    experience_profile_turn: str,
    experience_profile_context_mode: str,
    stderr: TextIO,
) -> bool:
    """Drive one USER_CHAT_BOOTSTRAP/settled turn that must call ``companion_set_experience_profile``."""
    if not _wait_ws_turn_settled(
        bridge,
        report,
        label="pre-experience_profile",
        settle_quiet_sec=_BOOTSTRAP_TURN_SETTLE_QUIET_SEC,
        max_sec=_BOOTSTRAP_TURN_SETTLE_MAX_SEC,
        stderr=stderr,
    ):
        report["errors"].append(
            {
                "turn": "pre-experience_profile",
                "error": (408, "ws not settled before experience_profile"),
            }
        )
    if not _wait_output_queue_idle(
        repo_root,
        config_path,
        agent_id=agent_id,
        timeout_sec=_BOOTSTRAP_TURN_SETTLE_MAX_SEC,
        label="pre-experience_profile",
        stderr=stderr,
    ):
        report["errors"].append(
            {
                "turn": "pre-experience_profile",
                "error": (408, "output queue not idle before experience_profile"),
            }
        )
    if not _wait_input_queue_idle(
        repo_root,
        config_path,
        agent_id=agent_id,
        timeout_sec=_TURN_REPLY_TIMEOUT_SEC,
        label="pre-experience_profile",
        stderr=stderr,
    ):
        report["errors"].append(
            {
                "turn": "pre-experience_profile",
                "error": (408, "input queue not idle before experience_profile"),
            }
        )
    print(f"{_TAG} experience_profile turn: {experience_profile_turn!r}", flush=True)
    experience_msg_uuid = _send_turn(bridge, agent_id, experience_profile_turn)
    text, meta, err = _wait_downlink_for_user_msg_uuid(
        bridge,
        report,
        expected_user_msg_uuid=experience_msg_uuid,
        timeout_sec=_TURN_REPLY_TIMEOUT_SEC,
        label="experience_profile",
        trailing_label="experience_profile_mismatch",
    )
    if err is not None:
        report["errors"].append({"turn": "experience_profile", "error": err})
        print(f"{_TAG} ERROR experience_profile: {err}", file=stderr, flush=True)
    else:
        assert text is not None
        report["turns"].append(
            {
                "kind": "experience_profile",
                "user": experience_profile_turn,
                "user_msg_uuid": experience_msg_uuid,
                "text_preview": text[:120],
                "meta": meta,
            }
        )
        print(
            f"{_TAG} experience_profile reply={text[:80]!r} "
            f"context_mode={meta.get('context_mode')}",
            flush=True,
        )
    _drain_turn_trailing_frames(bridge, report, label="experience_profile")
    if not _wait_input_delivered(
        repo_root,
        config_path,
        agent_id=agent_id,
        client_message_id=experience_msg_uuid,
        timeout_sec=_TURN_REPLY_TIMEOUT_SEC,
        label="experience_profile",
        stderr=stderr,
    ):
        report["errors"].append(
            {
                "turn": "experience_profile-delivered",
                "error": (408, f"input not delivered: {experience_msg_uuid}"),
            }
        )
    matched = _poll_context_mode(
        repo_root,
        config_path,
        user_id=user_id,
        agent_id=agent_id,
        expected=experience_profile_context_mode,
        timeout_sec=_EXPERIENCE_PROFILE_POLL_TIMEOUT_SEC,
        bridge=bridge,
        stderr=stderr,
    )
    report["experience_profile"] = {
        "expected_context_mode": experience_profile_context_mode,
        "matched": matched,
        "actual_context_mode": _query_context_mode(
            repo_root,
            config_path,
            user_id=user_id,
            agent_id=agent_id,
        ),
    }
    if not matched:
        report["errors"].append(
            {
                "turn": "experience_profile",
                "error": (
                    422,
                    f"context_mode != {experience_profile_context_mode!r}",
                ),
            }
        )
    return matched


def run_regression(
    *,
    repo_root: Path,
    agent_id: str,
    api_base: str,
    config_path: Path,
    user_id: str,
    bootstrap_turns: tuple[str, ...],
    bootstrap_finish_turn: str,
    experience_profile_turn: str,
    experience_profile_context_mode: str,
    settled_turn: str,
    proactive_wait_sec: float,
    proactive_min_rounds: int,
    proactive_target_rounds: int,
    dreaming_wait_sec: float,
    report_path: Path,
    token_path: str,
    stderr: TextIO,
) -> int:
    os.environ["INTY_CONFIG_YAML"] = str(config_path.resolve())
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
        "github_issue": {},
        "greeting": {},
        "bootstrap_memdocs": {},
        "experience_profile": {},
        "dreaming": {},
    }
    print(f"{_TAG} agent_id={agent_id}", flush=True)
    run_started_at_utc = datetime.now(timezone.utc)
    github_result = GithubIssueE2eResult(
        "",
        "",
        0,
        False,
        False,
        False,
        "skipped: regression did not reach github_issue phase",
    )
    greeting_result = ImplicitSignOnGreetingResult(
        present=False,
        source_greeting=False,
        text_preview="",
        langsmith_trace_id="",
    )
    memdoc_result = BootstrapMemDocResult(
        user_customized=False,
        identity_customized=False,
        style_customized=False,
        soul_unchanged=False,
        memory_unchanged=False,
        user_sequence_id=0,
        identity_sequence_id=0,
        style_sequence_id=0,
        memory_sequence_id=0,
        errors=("skipped: regression did not reach bootstrap memdoc phase",),
        warnings=(),
    )
    experience_profile_ok = False
    dreaming_result = DreamingConsolidationResult(
        checkpoint_present=False,
        memory_updated=False,
        memory_sequence_before=0,
        memory_sequence_after=0,
        error="skipped: regression did not reach dreaming phase",
    )
    bridge.start(connect_timeout=45.0)
    try:
        print(f"{_TAG} waiting for implicit greeting...", flush=True)
        greeting_turns: list[dict[str, Any]] = []
        text, meta, err = _wait_implicit_sign_on_greeting(
            bridge,
            timeout_sec=_TURN_REPLY_TIMEOUT_SEC,
        )
        if err is not None:
            report["errors"].append({"turn": "implicit_sign_on_greeting", "error": err})
            print(f"{_TAG} ERROR implicit_sign_on_greeting: {err}", file=stderr, flush=True)
        elif text is not None:
            turn_row = {
                "kind": "greeting",
                "text_preview": text[:120],
                "meta": meta,
            }
            greeting_turns.append(turn_row)
            report["turns"].append(turn_row)
            print(
                f"{_TAG} greeting text={text[:80]!r} source={meta.get('source')!r} "
                f"langsmith_trace_id={meta.get('langsmith_trace_id')}",
                flush=True,
            )
            for extra_text, extra_meta in _drain_until_quiet(
                bridge, quiet_sec=2.0, max_sec=15.0
            ):
                extra_row = {
                    "kind": "greeting_trailing",
                    "text_preview": extra_text[:120],
                    "meta": extra_meta,
                }
                greeting_turns.append(extra_row)
                report["turns"].append(extra_row)
        greeting_result = _verify_implicit_sign_on_greeting(greeting_turns)
        report["greeting"] = {
            "present": greeting_result.present,
            "source_greeting": greeting_result.source_greeting,
            "text_preview": greeting_result.text_preview,
            "langsmith_trace_id": greeting_result.langsmith_trace_id,
        }
        if not greeting_result.present:
            report["errors"].append(
                {
                    "turn": "implicit_sign_on_greeting",
                    "error": (
                        404,
                        "no non-empty WS downlink with meta_data.source=greeting",
                    ),
                }
            )
            print(
                f"{_TAG} ERROR implicit_sign_on_greeting missing",
                file=stderr,
                flush=True,
            )

        for idx, user_text in enumerate(bootstrap_turns, start=1):
            print(f"{_TAG} bootstrap turn {idx}: {user_text!r}", flush=True)
            bootstrap_msg_uuid = _send_turn(bridge, agent_id, user_text)
            text, meta, err = _wait_downlink_for_user_msg_uuid(
                bridge,
                report,
                expected_user_msg_uuid=bootstrap_msg_uuid,
                timeout_sec=_TURN_REPLY_TIMEOUT_SEC,
                label=f"bootstrap-{idx}",
                trailing_label=f"bootstrap-{idx}_mismatch",
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
                    "user_msg_uuid": bootstrap_msg_uuid,
                    "text_preview": text[:120],
                    "meta": meta,
                }
            )
            print(
                f"{_TAG} reply preview={text[:80]!r} "
                f"context_mode={meta.get('context_mode')}",
                flush=True,
            )
            _drain_turn_trailing_frames(
                bridge, report, label=f"bootstrap-{idx}"
            )
            if not _wait_input_delivered(
                repo_root,
                config_path,
                agent_id=agent_id,
                client_message_id=bootstrap_msg_uuid,
                timeout_sec=_TURN_REPLY_TIMEOUT_SEC,
                label=f"bootstrap-{idx}",
                stderr=stderr,
            ):
                report["errors"].append(
                    {
                        "turn": f"bootstrap-{idx}-delivered",
                        "error": (408, f"input not delivered: {bootstrap_msg_uuid}"),
                    }
                )
            if idx == len(bootstrap_turns):
                if not _wait_ws_turn_settled(
                    bridge,
                    report,
                    label=f"bootstrap-{idx}",
                    settle_quiet_sec=_BOOTSTRAP_TURN_SETTLE_QUIET_SEC,
                    max_sec=_BOOTSTRAP_TURN_SETTLE_MAX_SEC,
                    stderr=stderr,
                ):
                    report["errors"].append(
                        {
                            "turn": f"bootstrap-{idx}-settled",
                            "error": (
                                408,
                                f"bootstrap turn {idx} ws not settled before experience_profile",
                            ),
                        }
                    )

        experience_profile_ok = _run_experience_profile_phase(
            bridge=bridge,
            report=report,
            repo_root=repo_root,
            config_path=config_path,
            agent_id=agent_id,
            user_id=user_id,
            experience_profile_turn=experience_profile_turn,
            experience_profile_context_mode=experience_profile_context_mode,
            stderr=stderr,
        )

        print(f"{_TAG} bootstrap finish turn: {bootstrap_finish_turn!r}", flush=True)
        bootstrap_finish_msg_uuid = _send_turn(bridge, agent_id, bootstrap_finish_turn)
        text, meta, err = _wait_downlink_for_user_msg_uuid(
            bridge,
            report,
            expected_user_msg_uuid=bootstrap_finish_msg_uuid,
            timeout_sec=_TURN_REPLY_TIMEOUT_SEC,
            label="bootstrap-finish",
            trailing_label="bootstrap-finish_mismatch",
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
                    "user_msg_uuid": bootstrap_finish_msg_uuid,
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
        if not _wait_input_queue_idle(
            repo_root,
            config_path,
            agent_id=agent_id,
            timeout_sec=_TURN_REPLY_TIMEOUT_SEC,
            label="pre-settled",
            stderr=stderr,
        ):
            report["errors"].append(
                {"turn": "pre-settled", "error": (408, "input queue not idle")}
            )
        else:
            memdoc_result = _verify_bootstrap_memdocs(
                repo_root,
                config_path,
                user_id=user_id,
                agent_id=agent_id,
            )
            report["bootstrap_memdocs"] = {
                "user_customized": memdoc_result.user_customized,
                "identity_customized": memdoc_result.identity_customized,
                "style_customized": memdoc_result.style_customized,
                "soul_unchanged": memdoc_result.soul_unchanged,
                "memory_unchanged": memdoc_result.memory_unchanged,
                "user_sequence_id": memdoc_result.user_sequence_id,
                "identity_sequence_id": memdoc_result.identity_sequence_id,
                "style_sequence_id": memdoc_result.style_sequence_id,
                "memory_sequence_id": memdoc_result.memory_sequence_id,
                "errors": list(memdoc_result.errors),
                "warnings": list(memdoc_result.warnings),
            }
            if memdoc_result.errors:
                report["errors"].append(
                    {
                        "turn": "bootstrap_memdocs",
                        "error": (422, "; ".join(memdoc_result.errors)),
                    }
                )
                print(
                    f"{_TAG} ERROR bootstrap_memdocs: {memdoc_result.errors}",
                    file=stderr,
                    flush=True,
                )
            else:
                print(
                    f"{_TAG} bootstrap_memdocs ok "
                    f"user_seq={memdoc_result.user_sequence_id} "
                    f"identity_seq={memdoc_result.identity_sequence_id} "
                    f"style_seq={memdoc_result.style_sequence_id}",
                    flush=True,
                )
            if memdoc_result.warnings:
                print(
                    f"{_TAG} bootstrap_memdocs warnings: {memdoc_result.warnings}",
                    flush=True,
                )

        for text, meta in _drain_until_quiet(
            bridge,
            quiet_sec=_PRE_SETTLED_WS_DRAIN_QUIET_SEC,
            max_sec=30.0,
        ):
            _record_trailing_downlink(
                report,
                label="pre_settled",
                text=text,
                meta=meta,
            )

        print(f"{_TAG} settled turn: {settled_turn!r}", flush=True)
        settled_msg_uuid = _send_turn(bridge, agent_id, settled_turn)
        text, meta, err = _wait_downlink_for_user_msg_uuid(
            bridge,
            report,
            expected_user_msg_uuid=settled_msg_uuid,
            timeout_sec=_TURN_REPLY_TIMEOUT_SEC,
            label="settled",
            trailing_label="settled_mismatch",
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
                    "user_msg_uuid": settled_msg_uuid,
                    "text_preview": text[:120],
                    "meta": meta,
                }
            )
            print(
                f"{_TAG} settled reply={text[:80]!r} "
                f"user_msg_uuid={settled_msg_uuid} "
                f"langsmith_trace_id={meta.get('langsmith_trace_id')}",
                flush=True,
            )
        _drain_turn_trailing_frames(bridge, report, label="settled")

        settled_input_delivered = _wait_input_delivered(
            repo_root,
            config_path,
            agent_id=agent_id,
            client_message_id=settled_msg_uuid,
            timeout_sec=_TURN_REPLY_TIMEOUT_SEC,
            label="settled",
            stderr=stderr,
        )
        if not settled_input_delivered:
            report["errors"].append(
                {
                    "turn": "settled-delivered",
                    "error": (408, f"input not delivered: {settled_msg_uuid}"),
                }
            )
            github_result = GithubIssueE2eResult(
                "",
                "",
                0,
                False,
                False,
                False,
                "skipped: settled input not delivered",
            )
            report["github_issue"] = _github_issue_e2e_result_to_report(
                github_result
            )
        else:
            # TODO(#3606): Move github_issue_e2e to report-only / --eval; live LLM tool-call
            # compliance is model eval, not repeatable regression.
            github_result = _run_github_issue_e2e_phase(
                bridge=bridge,
                report=report,
                repo_root=repo_root,
                config_path=config_path,
                agent_id=agent_id,
                user_id=user_id,
                turn_text=_DEFAULT_GITHUB_ISSUE_TURN,
                stderr=stderr,
            )
            report["github_issue"] = _github_issue_e2e_result_to_report(
                github_result
            )
            if github_result.error is not None:
                report["errors"].append(
                    {
                        "turn": "github_issue_e2e",
                        "error": (500, github_result.error),
                    }
                )

            print(
                f"{_TAG} waiting up to {proactive_wait_sec}s for proactive inner-tick "
                f"(pass >={proactive_min_rounds} round(s), target {proactive_target_rounds}; "
                f"idle 10s + poll 3s; after github_issue)...",
                flush=True,
            )
            proactive_deadline = time.monotonic() + proactive_wait_sec
            while time.monotonic() < proactive_deadline:
                text, meta, err = _wait_downlink(
                    bridge,
                    timeout_sec=min(
                        _PROACTIVE_RECV_CHUNK_SEC,
                        proactive_deadline - time.monotonic(),
                    ),
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
                        "silent": False,
                    }
                )
                print(
                    f"{_TAG} proactive text={text[:80]!r} "
                    f"langsmith_trace_id={meta.get('langsmith_trace_id')} "
                    f"round={len(report['proactive']) + 1}",
                    flush=True,
                )
            print(
                f"{_TAG} post-proactive drain "
                f"(quiet={_POST_PROACTIVE_DRAIN_QUIET_SEC}s, "
                f"max={_POST_PROACTIVE_DRAIN_MAX_SEC}s) before disconnect...",
                flush=True,
            )
            for text, meta in _drain_until_quiet(
                bridge,
                quiet_sec=_POST_PROACTIVE_DRAIN_QUIET_SEC,
                max_sec=_POST_PROACTIVE_DRAIN_MAX_SEC,
            ):
                if str(meta.get("source") or "") == "chat":
                    _record_trailing_downlink(
                        report,
                        label="post_proactive",
                        text=text,
                        meta=meta,
                    )

            memory_doc = _query_latest_memdoc_version(
                repo_root,
                config_path,
                user_id=user_id,
                agent_id=agent_id,
                document_kind="memory",
            )
            memory_seq_before_dreaming = (
                memory_doc.sequence_id if memory_doc else 0
            )
            print(
                f"{_TAG} waiting up to {dreaming_wait_sec}s for dreaming consolidation "
                f"(scope worker; dreaming_idle_seconds=10 in config; "
                f"memory_sequence_before={memory_seq_before_dreaming})...",
                flush=True,
            )
            dreaming_result = _wait_dreaming_consolidation(
                repo_root,
                config_path,
                user_id=user_id,
                agent_id=agent_id,
                memory_sequence_before=memory_seq_before_dreaming,
                wait_sec=dreaming_wait_sec,
                stderr=stderr,
            )
            report["dreaming"] = {
                "checkpoint_present": dreaming_result.checkpoint_present,
                "memory_updated": dreaming_result.memory_updated,
                "memory_sequence_before": dreaming_result.memory_sequence_before,
                "memory_sequence_after": dreaming_result.memory_sequence_after,
                "error": dreaming_result.error,
            }
            if dreaming_result.error:
                report["errors"].append(
                    {"turn": "dreaming", "error": (408, dreaming_result.error)}
                )
                print(
                    f"{_TAG} ERROR dreaming: {dreaming_result.error}",
                    file=stderr,
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

    proactive_summary = _finalize_proactive_report(
        report,
        repo_root=repo_root,
        config_path=config_path,
        user_id=user_id,
        agent_id=agent_id,
        run_started_at_utc=run_started_at_utc,
        proactive_min_rounds=proactive_min_rounds,
        proactive_target_rounds=proactive_target_rounds,
    )

    ctx_line = ctx_rows.strip().split("\n")[0] if ctx_rows.strip() else ""
    parts = ctx_line.split("|") if ctx_line else []
    bootstrap_done = parts[2] if len(parts) >= 3 else "unknown"
    context_mode = parts[1] if len(parts) >= 2 else "unknown"

    proactive_present = proactive_summary["total"] >= proactive_min_rounds
    proactive_target_met = proactive_summary["total"] >= proactive_target_rounds
    proactive_silent_ok = proactive_summary["silent_token_leaks"] == 0
    settled_ok = any(
        t.get("kind") == "settled"
        and t.get("text_preview")
        and t.get("user_msg_uuid")
        for t in report["turns"]
    )
    in_all_delivered = (
        "pending" not in in_q
        and "claimed" not in in_q
        and "failed" not in in_q
        and bool(in_q.strip())
    )
    out_all_delivered = (
        "pending" not in out_q
        and "failed" not in out_q
        and "skipped" not in out_q
        and bool(out_q.strip())
    )

    companion_bond_state = _query_active_companion_bond_agent_id(
        repo_root,
        config_path,
        user_id=user_id,
        agent_id=agent_id,
    )
    report["companion_bond"] = {
        "user_id": user_id,
        "agent_id": agent_id,
        "state": companion_bond_state,
    }

    app_debug = _load_app_debug_from_config(config_path)
    github_issue_ok = github_result.error is None and github_result.closed
    github_disclosure_ok = (
        not app_debug or github_result.disclosed_in_chat
    )

    summary = {
        "bootstrap": "complete" if bootstrap_done == "true" else "incomplete",
        "context_mode": context_mode,
        "implicit_sign_on_greeting": (
            "pass" if greeting_result.present else "fail"
        ),
        "bootstrap_memdocs": (
            "pass" if not memdoc_result.errors else "fail"
        ),
        "experience_profile": "pass" if experience_profile_ok else "fail",
        "dreaming_consolidation": (
            "pass" if dreaming_result.error is None else "fail"
        ),
        "settled_queue_turn": "pass" if settled_ok and not report["errors"] else "fail",
        "github_issue_e2e": "pass" if github_issue_ok else "fail",
        "github_issue_disclosed_in_chat": (
            "pass"
            if github_disclosure_ok and github_issue_ok
            else "fail"
            if app_debug
            else "skipped"
        ),
        "proactive_inner_tick": "present" if proactive_present else "missing",
        "proactive_target_rounds": "met" if proactive_target_met else "miss",
        "proactive_silent_rounds": proactive_summary["silent"],
        "proactive_visible_rounds": proactive_summary["visible"],
        "proactive_no_silent_token": "pass" if proactive_silent_ok else "fail",
        "companion_bond_state": companion_bond_state or "missing",
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

    # TODO(#3606): ``github_issue_ok`` gates on live model tool use; keep infra checks
    # mandatory and move LLM-behavior phases to optional eval report.
    passed = (
        settled_ok
        and not report["errors"]
        and in_all_delivered
        and out_all_delivered
        and bootstrap_done == "true"
        and greeting_result.present
        and not memdoc_result.errors
        and experience_profile_ok
        and proactive_present
        and proactive_silent_ok
        and github_issue_ok
        and github_disclosure_ok
        and dreaming_result.error is None
    )
    return 0 if passed else 1


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
        default=_DEFAULT_PROACTIVE_WAIT_SEC,
        help=(
            "Seconds to wait for inner-tick proactive rounds after settled turn "
            f"(default {_DEFAULT_PROACTIVE_WAIT_SEC:g}; pairs with 10s idle + 3s poll)"
        ),
    )
    p.add_argument(
        "--proactive-min-rounds",
        type=int,
        default=_DEFAULT_PROACTIVE_MIN_ROUNDS,
        help=(
            "Minimum proactive rounds to pass (WS downlink and/or DB synthetic user rows; "
            f"default {_DEFAULT_PROACTIVE_MIN_ROUNDS}; silent-first blocks a 2nd round)"
        ),
    )
    p.add_argument(
        "--proactive-target-rounds",
        type=int,
        default=_DEFAULT_PROACTIVE_TARGET_ROUNDS,
        help=(
            "Stretch proactive round count for summary only (default "
            f"{_DEFAULT_PROACTIVE_TARGET_ROUNDS}; does not fail the run)"
        ),
    )
    p.add_argument(
        "--dreaming-wait-sec",
        type=float,
        default=_DEFAULT_DREAMING_WAIT_SEC,
        help=(
            "Seconds to poll for scope-worker dreaming + MEMORY.md update after proactive "
            f"(default {_DEFAULT_DREAMING_WAIT_SEC:g}; pairs with dreaming_idle_seconds=10; scope-worker batches may take minutes)"
        ),
    )
    p.add_argument(
        "--report",
        default="",
        help="JSON report path (default: tmp/repl-regression-<agent_id>.json)",
    )
    p.add_argument(
        "--create-timeout",
        type=float,
        default=60.0,
        help="HTTP timeout for --create-agent (default 60)",
    )
    args = p.parse_args(argv)

    _ensure_import_path(repo_root)
    config_path = Path(str(args.config).strip())
    if not config_path.is_absolute():
        config_path = repo_root / config_path
    if not config_path.is_file():
        print(f"error: config not found: {config_path}", file=sys.stderr)
        return 2

    agent_id = str(args.agent_id).strip()
    if args.create_agent:
        if agent_id:
            print(
                f"{_TAG} warning: --agent-id ignored when --create-agent is set",
                file=sys.stderr,
            )
        remaining = _deactivate_active_companion_bonds_for_user(
            repo_root,
            config_path,
            user_id=str(args.user_id).strip(),
        )
        if remaining:
            print(
                f"{_TAG} warning: {remaining} ACTIVE companion bond(s) remain for "
                f"user {args.user_id!r} after deactivate",
                file=sys.stderr,
            )
        else:
            print(
                f"{_TAG} deactivated prior ACTIVE companion bonds for "
                f"user {args.user_id!r}",
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
    proactive_min_rounds = int(args.proactive_min_rounds)
    if proactive_min_rounds < 1:
        print("error: --proactive-min-rounds must be >= 1", file=sys.stderr)
        return 2
    proactive_target_rounds = int(args.proactive_target_rounds)
    if proactive_target_rounds < proactive_min_rounds:
        print(
            "error: --proactive-target-rounds must be >= --proactive-min-rounds",
            file=sys.stderr,
        )
        return 2
    dreaming_wait = float(args.dreaming_wait_sec)
    if dreaming_wait < 0:
        print("error: --dreaming-wait-sec must be >= 0", file=sys.stderr)
        return 2

    return run_regression(
        repo_root=repo_root,
        agent_id=agent_id,
        api_base=str(args.api_base).strip(),
        config_path=config_path,
        user_id=str(args.user_id).strip(),
        bootstrap_turns=_DEFAULT_BOOTSTRAP_TURNS,
        bootstrap_finish_turn=_DEFAULT_BOOTSTRAP_FINISH_TURN,
        experience_profile_turn=_DEFAULT_EXPERIENCE_PROFILE_TURN,
        experience_profile_context_mode=_DEFAULT_EXPERIENCE_PROFILE_CONTEXT_MODE,
        settled_turn=_DEFAULT_SETTLED_TURN,
        proactive_wait_sec=proactive_wait,
        proactive_min_rounds=proactive_min_rounds,
        proactive_target_rounds=proactive_target_rounds,
        dreaming_wait_sec=dreaming_wait,
        report_path=report_path,
        token_path=str(args.token_file).strip(),
        stderr=sys.stderr,
    )


if __name__ == "__main__":
    raise SystemExit(main())
