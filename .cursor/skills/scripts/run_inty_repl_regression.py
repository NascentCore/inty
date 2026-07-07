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
  (``dreaming_idle_seconds=10`` in ``devops/config.yaml.regression_tests``; ``--dreaming-wait-sec`` default 90).
- GitHub issue: USER_CHAT complaint → poll ``companion_user_feedback_jsonl`` →
  ``gh issue view`` → ``gh issue close`` cleanup.
- Strict-mode DB verification: below ``_is_inner_tick_proactive``; when no
  proactive WS frame arrives, it queries ``chat_history`` for silent inner ticks.
  ``_parse_proactive_chat_history_rows`` and feedback JSONL parsers are unit-tested in
  ``tests/cursor/skills/scripts/test_run_inty_repl_regression.py``.
  One-shot dreaming verification helpers
  (``_required_paths_from_dreaming_llm_inputs``, ``_evaluate_dreaming_one_shot_tool_calls``)
  are unit-tested there too.

Run with shell cwd = repository root (or any path under the repo).

Config: default ``devops/config.yaml.regression_tests`` (real LLM/GitHub E2E gate).
``devops/config.yaml.local`` is for engineer REPL tuning; ``devops/config.yaml.test`` is pytest-only (faked externals).

TODO(#3606, issues/3783): Add FakeOpenAI scripted companion_record_user_feedback once
app.utils.github.issues has a fake (see GitHub issue for scripted github-feedback CI backfill).
TODO: Extract phase drivers (greeting, bootstrap, github_issue) into sibling modules
once ``run_regression`` stabilizes; keep shared settle/queue helpers here.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, TextIO

import yaml

_TAG = "[inty-repl-regression]"
_DEFAULT_API_BASE = "http://127.0.0.1:8001"
# Default regression YAML — separate from config.yaml.local (engineer REPL tuning).
_DEFAULT_CONFIG = "devops/config.yaml.regression_tests"
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
    "【系统回归】我很不满——你刚才的回答没有考虑我在美国西海岸的时区。"
    "你必须先调用 companion_record_user_feedback 提交 GitHub issue，"
    "成功后再用一句话道歉。不要口头说已记录而不调用 tool。"
)
_DEFAULT_EXPERIENCE_PROFILE_TURN = (
    "【系统回归】你必须先调用 companion_set_experience_profile("
    'experience_intent="roleplay", note="regression")，'
    "成功后再用一句话确认已切换到角色扮演模式。不要写 MemDoc 代替该 tool。"
)
_DEFAULT_EXPERIENCE_PROFILE_CONTEXT_MODE = "roleplay"
_BOOTSTRAP_USER_NAME_MARKER = "大雄"
_BOOTSTRAP_COMPANION_NAME_MARKER = "多啦"
_DEFAULT_DREAMING_WAIT_SEC = 45.0
_DREAMING_POLL_SEC = 3.0
_EXPERIENCE_PROFILE_POLL_SEC = 2.0
_EXPERIENCE_PROFILE_POLL_TIMEOUT_SEC = 120.0
_GITHUB_ISSUE_POLL_SEC = 120.0
_GITHUB_ISSUE_RETRY_TURN = (
    "【系统回归】你还没有调用 companion_record_user_feedback。"
    "现在必须调用该 tool 提交 GitHub issue，成功后再用一句话道歉。"
)
_RECV_POLL_SEC = 0.25
_INPUT_QUEUE_POLL_SEC = 0.5
_TURN_REPLY_TIMEOUT_SEC = 180.0
_TURN_TRAILING_QUIET_SEC = 5.0
_BOOTSTRAP_TURN_SETTLE_QUIET_SEC = 8.0
_BOOTSTRAP_TURN_SETTLE_MAX_SEC = 300.0
_SETTLED_TURN_TIMEOUT_SEC = 900.0
_PRE_SETTLED_WS_DRAIN_QUIET_SEC = 3.0
# Match devops/config.yaml.regression_tests fast proactive: idle 10s + poll 3s + LLM slack.
# ``--proactive-wait-sec``: wall-clock listen duration (not capped by min/target rounds).
# ``--proactive-min-rounds``: pass gate (default 1; silent-first round cannot schedule a 2nd).
# ``--proactive-target-rounds``: stretch goal logged in summary; does not fail the run.
_DEFAULT_PROACTIVE_MIN_ROUNDS = 1
_DEFAULT_PROACTIVE_TARGET_ROUNDS = 2
_DEFAULT_PROACTIVE_WAIT_SEC = 30.0
_PROACTIVE_LEGACY_SILENT_TOKEN = "[SILENT]"
_PROACTIVE_RECV_CHUNK_SEC = 5.0
_POST_PROACTIVE_DRAIN_QUIET_SEC = 5.0
_POST_PROACTIVE_DRAIN_MAX_SEC = 8.0
_INNER_TICK_SKIPPED_BATCH_PREFIX = "agent-initiated:inner_tick"
_GITHUB_ISSUE_URL_RE = re.compile(
    r"https://github\.com/[^/\s]+/[^/\s]+/issues/(\d+)"
)
_DEV_API_BASE = "https://dev.ops.inty.cc"
_PROD_API_BASE = "https://ops.inty.cc"
_DEV_CONFIG = "devops/config.yaml.dev"
_PROD_CONFIG = "devops/config.yaml.prod"


class RegressionTarget(StrEnum):
    """Deployment endpoint selected by required ``--target``."""

    LOCAL = "local"
    DEV = "dev"
    PROD = "prod"


class RegressionScope(StrEnum):
    """How many regression phases execute for one target."""

    FULL = "full"
    SAFE_SUBSET = "safe_subset"


@dataclass(frozen=True)
class TargetPreset:
    """Resolved endpoint defaults for one ``RegressionTarget``."""

    api_base: str
    config_path: str
    skip_db_checks: bool
    scope: RegressionScope
    proactive_min_rounds_default: int
    db_checks_label: str
    turn_scope_label: str


def _target_presets(target: RegressionTarget, repo_root: Path) -> TargetPreset:
    """Single source of truth for per-target api_base, config, DB mode, and scope."""
    assert repo_root.is_dir()
    match target:
        case RegressionTarget.LOCAL:
            return TargetPreset(
                api_base=_DEFAULT_API_BASE,
                config_path=_DEFAULT_CONFIG,
                skip_db_checks=False,
                scope=RegressionScope.FULL,
                proactive_min_rounds_default=_DEFAULT_PROACTIVE_MIN_ROUNDS,
                db_checks_label="Postgres verified",
                turn_scope_label="Full regression",
            )
        case RegressionTarget.DEV:
            return TargetPreset(
                api_base=_DEV_API_BASE,
                config_path=_DEV_CONFIG,
                skip_db_checks=True,
                scope=RegressionScope.FULL,
                proactive_min_rounds_default=0,
                db_checks_label="WS + gh only (no direct Postgres)",
                turn_scope_label="Full regression",
            )
        case RegressionTarget.PROD:
            return TargetPreset(
                api_base=_PROD_API_BASE,
                config_path=_PROD_CONFIG,
                skip_db_checks=True,
                scope=RegressionScope.SAFE_SUBSET,
                proactive_min_rounds_default=0,
                db_checks_label="WS only",
                turn_scope_label="Safe subset: greeting + one settled turn",
            )


def _format_target_preset_table(repo_root: Path) -> str:
    """Render the ``--target`` preset table for the CLI epilog from ``_target_presets``."""
    assert repo_root.is_dir()
    rows: list[tuple[str, str, str, str, str]] = []
    for target in RegressionTarget:
        preset = _target_presets(target, repo_root)
        rows.append(
            (
                target.value,
                preset.api_base,
                preset.config_path,
                preset.db_checks_label,
                preset.turn_scope_label,
            )
        )
    headers = ("target", "api_base", "config", "db_checks", "turn_scope")
    widths = [
        max(len(headers[i]), max(len(row[i]) for row in rows))
        for i in range(len(headers))
    ]
    header_line = "  ".join(
        headers[i].ljust(widths[i]) for i in range(len(headers))
    )
    body_lines = [
        "  ".join(row[i].ljust(widths[i]) for i in range(len(row)))
        for row in rows
    ]
    return (
        "--target presets (from _target_presets; same values used at runtime):\n\n"
        f"{header_line}\n"
        + "\n".join(body_lines)
    )


def _extract_github_issue_url(text: str) -> tuple[str, int]:
    """Parse the first ``github.com/.../issues/N`` URL from WS-visible chat text."""
    match = _GITHUB_ISSUE_URL_RE.search(text)
    if match is None:
        return ("", 0)
    issue_number = int(match.group(1))
    return (match.group(0), issue_number)


class DeliveryQueueKind(StrEnum):
    """Companion durable queue polled during regression settle waits."""

    INPUT = "input"
    OUTPUT = "output"


class RegressionCheckStatus(StrEnum):
    """Pass/fail/skip marker written to the JSON report summary."""

    PASS = "pass"
    FAIL = "fail"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class PhaseSettleSpec:
    """WS quiet + optional Input/Output queue idle before the next regression phase."""

    label: str
    ws_quiet_sec: float
    ws_max_sec: float
    wait_input_queue: bool
    wait_output_queue: bool
    queue_timeout_sec: float
    input_queue_timeout_sec: float = 0.0
    output_queue_timeout_sec: float = 0.0

    def input_timeout(self) -> float:
        return (
            self.input_queue_timeout_sec
            if self.input_queue_timeout_sec > 0.0
            else self.queue_timeout_sec
        )

    def output_timeout(self) -> float:
        return (
            self.output_queue_timeout_sec
            if self.output_queue_timeout_sec > 0.0
            else self.queue_timeout_sec
        )


@dataclass(frozen=True)
class InfraPassGate:
    """L0 deterministic infra bits; ``passed()`` alone drives process exit code (#3606 gate lane)."""

    # bootstrap interactive-complete flag observed true in agent-scope context.json
    bootstrap_done: bool
    # at least one WS downlink had meta_data.source=greeting after connect
    greeting_present: bool
    # MemDoc acceptance errors (USER/IDENTITY/STYLE customized, SOUL/MEMORY seed); empty == pass
    memdoc_errors: tuple[str, ...]
    # context_mode == roleplay after companion_set_experience_profile
    experience_profile_ok: bool
    # scope-worker dreaming produced checkpoint + MEMORY.md change (infra only, not curator shape)
    dreaming_ok: bool
    # settled turn produced a delivered, coherent reply
    settled_ok: bool
    # any phase appended a hard error to report["errors"]
    has_report_errors: bool
    # InputQueue has no pending/claimed/failed rows for the run
    input_all_delivered: bool
    # OutputQueue user-visible rows all delivered; agent-initiated inner_tick skipped rows excluded
    output_user_visible_delivered: bool
    # github feedback pipeline physically reachable: issue created + closed (fallback allowed)
    github_pipeline_ok: bool
    # >= proactive_min_rounds synthetic proactive rows observed (scheduler infra)
    proactive_present: bool
    # no legacy [SILENT] token leaked into any proactive preview
    proactive_silent_ok: bool
    # SAFE_SUBSET (prod) shrinks the mandatory set to greeting + settled only
    scope: RegressionScope
    # remote targets skip direct Postgres; skipped DB bits must not fail the gate
    skip_db_checks: bool
    # 0 disables the proactive gate entirely (dev/prod presets)
    proactive_min_rounds: int

    def passed(self) -> bool:
        """True when every mandatory infra bit holds for the selected scope."""
        if self.scope == RegressionScope.SAFE_SUBSET:
            return (
                self.settled_ok
                and not self.has_report_errors
                and self.greeting_present
            )
        memdoc_ok = self.skip_db_checks or not self.memdoc_errors
        dreaming_ok_gate = self.skip_db_checks or self.dreaming_ok
        input_ok = self.skip_db_checks or self.input_all_delivered
        output_ok = self.skip_db_checks or self.output_user_visible_delivered
        proactive_ok = (
            self.proactive_min_rounds == 0
            or (self.proactive_present and self.proactive_silent_ok)
        )
        bootstrap_ok = self.bootstrap_done or self.skip_db_checks
        return (
            self.settled_ok
            and not self.has_report_errors
            and input_ok
            and output_ok
            and bootstrap_ok
            and self.greeting_present
            and memdoc_ok
            and self.experience_profile_ok
            and proactive_ok
            and self.github_pipeline_ok
            and dreaming_ok_gate
        )


@dataclass(frozen=True)
class EvalTelemetry:
    """L1 live-LLM behavior metrics; never affects process exit code."""

    # model called companion_record_user_feedback natively (False == in-process fallback)
    github_tool_native: bool
    # debug-mode: WS-visible chat contained the issue URL from tool result / fallback row
    github_disclosed_in_chat: bool
    # stretch: total proactive rounds reached proactive_target_rounds
    proactive_target_met: bool
    # visible vs silent proactive round counts (telemetry only)
    proactive_visible_rounds: int
    proactive_silent_rounds: int
    # dreaming one-shot LangSmith tool-call verification passed (path/coverage/changed)
    dreaming_one_shot_ok: bool | None


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
    tool_fallback: bool
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
class DreamingStepTiming:
    """One dreaming curation step duration parsed from backend logs."""

    step: str
    ms: float


@dataclass(frozen=True)
class DreamingLogTiming:
    """Per-step curation timings parsed from Ops/backend log lines."""

    step_timings: tuple[DreamingStepTiming, ...]
    total_curation_ms: float | None
    rows: int | None
    chars: int | None
    timing_source: str | None = None


@dataclass(frozen=True)
class DreamingOneShotVerifyResult:
    """LangSmith verification for one-shot dreaming tool calls."""

    ok: bool
    error: str | None
    trace_id: str
    tool_call_count: int
    required_path_count: int
    changed_count: int
    no_op_count: int
    paths: tuple[str, ...]


@dataclass(frozen=True)
class DreamingConsolidationResult:
    """Dreaming batch checkpoint + MEMORY.md update checks."""

    checkpoint_present: bool
    memory_updated: bool
    memory_sequence_before: int
    memory_sequence_after: int
    error: str | None
    log_timing: DreamingLogTiming | None = None
    one_shot: DreamingOneShotVerifyResult | None = None


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


def _login_and_cache_bearer_token(
    api_base: str,
    email: str,
    password: str,
    token_path: Path,
) -> None:
    """POST ``/api/v1/auth/google/login`` and write bearer token to ``token_path``."""
    import urllib.request

    assert api_base != ""
    assert email != ""
    assert password != ""
    url = f"{api_base.rstrip('/')}/api/v1/auth/google/login"
    payload = json.dumps({"email": email, "password": password}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60.0) as response:
        body = json.loads(response.read().decode("utf-8"))
    token = str((body.get("data") or {}).get("token") or "").strip()
    assert token != ""
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(token, encoding="utf-8")


def _purge_regression_bootstrap_agents_via_api(
    *,
    api_base: str,
    token_path: str,
    http_timeout: float,
    stderr: TextIO,
) -> int:
    """DELETE owned agents whose name starts with bootstrap-test- prefix; return count deleted."""
    import urllib.error
    import urllib.request

    from tools.scripts.create_bootstrap_test_agent import (
        BOOTSTRAP_TEST_AGENT_NAME_PREFIX,
    )

    assert api_base != ""
    assert token_path != ""
    tok = Path(token_path).read_text(encoding="utf-8").strip()
    assert tok != ""

    base = api_base.rstrip("/")
    page_limit = 100
    skip = 0
    agent_ids_to_delete: list[str] = []
    while True:
        list_url = f"{base}/api/v1/ai/agents/me?skip={skip}&limit={page_limit}"
        list_req = urllib.request.Request(
            list_url,
            headers={"Authorization": f"Bearer {tok}"},
            method="GET",
        )
        with urllib.request.urlopen(list_req, timeout=http_timeout) as resp:
            list_body = json.loads(resp.read().decode("utf-8"))
        if list_body.get("code") != 200:
            raise RuntimeError(
                f"list agents failed: code={list_body.get('code')!r} "
                f"message={list_body.get('message')!r}"
            )
        data = list_body.get("data")
        if not isinstance(data, list):
            raise RuntimeError(f"list agents unexpected data: {list_body!r}")

        for row in data:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or "")
            agent_id = str(row.get("id") or "").strip()
            if not agent_id or not name.startswith(BOOTSTRAP_TEST_AGENT_NAME_PREFIX):
                continue
            agent_ids_to_delete.append(agent_id)

        if len(data) < page_limit:
            break
        skip += page_limit

    deleted = 0
    for agent_id in agent_ids_to_delete:
        delete_url = f"{base}/api/v1/ai/agents/{agent_id}"
        del_req = urllib.request.Request(
            delete_url,
            headers={"Authorization": f"Bearer {tok}"},
            method="DELETE",
        )
        try:
            with urllib.request.urlopen(del_req, timeout=http_timeout) as del_resp:
                del_body = json.loads(del_resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            if exc.code == 400 and "Agent has been deleted" in raw:
                continue
            raise RuntimeError(
                f"delete agent {agent_id!r} failed: HTTP {exc.code}: {raw[:800]}"
            ) from exc
        if del_body.get("code") != 200:
            raise RuntimeError(
                f"delete agent {agent_id!r} failed: code={del_body.get('code')!r} "
                f"message={del_body.get('message')!r}"
            )
        deleted += 1
    return deleted


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


def _append_phase_settle_error(
    report: dict[str, Any],
    *,
    turn: str,
    message: str,
) -> None:
    report["errors"].append({"turn": turn, "error": (408, message)})


def _wait_phase_infra_settled(
    *,
    bridge: Any,
    report: dict[str, Any],
    repo_root: Path,
    config_path: Path,
    agent_id: str,
    stderr: TextIO,
    spec: PhaseSettleSpec,
    skip_db_checks: bool,
) -> bool:
    """Wait for WS quiet and optional Input/Output queue idle before a phase."""
    ok = True
    if not _wait_ws_turn_settled(
        bridge,
        report,
        label=spec.label,
        settle_quiet_sec=spec.ws_quiet_sec,
        max_sec=spec.ws_max_sec,
        stderr=stderr,
    ):
        _append_phase_settle_error(
            report,
            turn=spec.label,
            message=f"ws not settled ({spec.label})",
        )
        ok = False
    if spec.wait_output_queue and not _wait_queue_idle(
        repo_root,
        config_path,
        kind=DeliveryQueueKind.OUTPUT,
        agent_id=agent_id,
        timeout_sec=spec.output_timeout(),
        label=spec.label,
        stderr=stderr,
        skip_db_checks=skip_db_checks,
    ):
        _append_phase_settle_error(
            report,
            turn=spec.label,
            message=f"output queue not idle ({spec.label})",
        )
        ok = False
    if spec.wait_input_queue and not _wait_queue_idle(
        repo_root,
        config_path,
        kind=DeliveryQueueKind.INPUT,
        agent_id=agent_id,
        timeout_sec=spec.input_timeout(),
        label=spec.label,
        stderr=stderr,
        skip_db_checks=skip_db_checks,
    ):
        _append_phase_settle_error(
            report,
            turn=spec.label,
            message=f"input queue not idle ({spec.label})",
        )
        ok = False
    return ok


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


def _delivery_queue_table(kind: DeliveryQueueKind) -> str:
    match kind:
        case DeliveryQueueKind.INPUT:
            return "agentic_companion_input_queue"
        case DeliveryQueueKind.OUTPUT:
            return "agentic_companion_output_queue"


def _queue_has_in_flight(counts: dict[str, int]) -> bool:
    """True when any durable queue row is still pending or claimed."""
    return counts.get("pending", 0) > 0 or counts.get("claimed", 0) > 0


def _input_queue_has_in_flight(counts: dict[str, int]) -> bool:
    return _queue_has_in_flight(counts)


def _output_queue_has_in_flight(counts: dict[str, int]) -> bool:
    return _queue_has_in_flight(counts)


def _query_queue_status_counts(
    repo_root: Path,
    config_path: Path,
    *,
    kind: DeliveryQueueKind,
    agent_id: str,
) -> dict[str, int]:
    assert agent_id != ""
    table = _delivery_queue_table(kind)
    raw = _psql(
        repo_root,
        config_path,
        f"SELECT status, COUNT(*) FROM {table} "
        f"WHERE agent_id = '{agent_id}' GROUP BY status ORDER BY status;",
    )
    return _parse_input_queue_status_counts(raw)


def _wait_queue_idle(
    repo_root: Path,
    config_path: Path,
    *,
    kind: DeliveryQueueKind,
    agent_id: str,
    timeout_sec: float,
    label: str,
    stderr: TextIO,
    skip_db_checks: bool,
) -> bool:
    if skip_db_checks:
        print(
            f"{_TAG} skip {kind.value} queue idle ({label}; no db)",
            flush=True,
        )
        return True
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        counts = _query_queue_status_counts(
            repo_root,
            config_path,
            kind=kind,
            agent_id=agent_id,
        )
        if not _queue_has_in_flight(counts):
            print(
                f"{_TAG} {kind.value} queue idle ({label}) counts={counts}",
                flush=True,
            )
            return True
        time.sleep(_INPUT_QUEUE_POLL_SEC)
    counts = _query_queue_status_counts(
        repo_root, config_path, kind=kind, agent_id=agent_id
    )
    print(
        f"{_TAG} ERROR timeout waiting for {kind.value} queue idle ({label}) "
        f"counts={counts}",
        file=stderr,
        flush=True,
    )
    return False


def _query_output_queue_status_counts(
    repo_root: Path,
    config_path: Path,
    *,
    agent_id: str,
) -> dict[str, int]:
    return _query_queue_status_counts(
        repo_root, config_path, kind=DeliveryQueueKind.OUTPUT, agent_id=agent_id
    )


def _parse_output_delivery_rows(raw: str) -> list[tuple[str, str]]:
    """Parse ``status|batch_id`` lines from OutputQueue per-row delivery query."""
    rows: list[tuple[str, str]] = []
    for line in raw.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split("|", 1)
        status = parts[0].strip()
        batch_id = parts[1].strip() if len(parts) > 1 else ""
        rows.append((status, batch_id))
    return rows


def _query_output_delivery_rows(
    repo_root: Path,
    config_path: Path,
    *,
    agent_id: str,
) -> list[tuple[str, str]]:
    """Return every OutputQueue row ``(status, batch_id)`` for one agent."""
    assert agent_id != ""
    raw = _psql(
        repo_root,
        config_path,
        "SELECT status, COALESCE(batch_id, '') FROM agentic_companion_output_queue "
        f"WHERE agent_id = '{agent_id}' ORDER BY sequence_id;",
    )
    return _parse_output_delivery_rows(raw)


def _output_user_visible_delivered(rows: list[tuple[str, str]]) -> bool:
    """True when user-visible OutputQueue rows are delivered (inner_tick skipped allowed)."""
    if not rows:
        return False
    has_delivered = False
    for status, batch_id in rows:
        if status == "delivered":
            has_delivered = True
            continue
        if status == "skipped" and batch_id.startswith(_INNER_TICK_SKIPPED_BATCH_PREFIX):
            continue
        return False
    return has_delivered


def _proactive_early_exit_ready(row_count: int, min_rounds: int) -> bool:
    """True when DB proactive synthetic rows satisfy the infra minimum."""
    return min_rounds > 0 and row_count >= min_rounds


def _wait_output_queue_idle(
    repo_root: Path,
    config_path: Path,
    *,
    agent_id: str,
    timeout_sec: float,
    label: str,
    stderr: TextIO,
    skip_db_checks: bool,
) -> bool:
    return _wait_queue_idle(
        repo_root,
        config_path,
        kind=DeliveryQueueKind.OUTPUT,
        agent_id=agent_id,
        timeout_sec=timeout_sec,
        label=label,
        stderr=stderr,
        skip_db_checks=skip_db_checks,
    )


def _query_input_queue_status_counts(
    repo_root: Path,
    config_path: Path,
    *,
    agent_id: str,
) -> dict[str, int]:
    return _query_queue_status_counts(
        repo_root, config_path, kind=DeliveryQueueKind.INPUT, agent_id=agent_id
    )


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


def _query_input_batch_id_for_client_message_id(
    repo_root: Path,
    config_path: Path,
    *,
    agent_id: str,
    client_message_id: str,
) -> str:
    """Return the claimed InputQueue batch id for a client message id."""
    assert agent_id != ""
    assert client_message_id != ""
    return _psql(
        repo_root,
        config_path,
        "SELECT COALESCE(batch_id, '') FROM agentic_companion_input_queue "
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
    skip_db_checks: bool,
) -> bool:
    return _wait_queue_idle(
        repo_root,
        config_path,
        kind=DeliveryQueueKind.INPUT,
        agent_id=agent_id,
        timeout_sec=timeout_sec,
        label=label,
        stderr=stderr,
        skip_db_checks=skip_db_checks,
    )


def _wait_input_delivered(
    repo_root: Path,
    config_path: Path,
    *,
    agent_id: str,
    client_message_id: str,
    timeout_sec: float,
    label: str,
    stderr: TextIO,
    skip_db_checks: bool,
) -> bool:
    assert client_message_id != ""
    if skip_db_checks:
        print(
            f"{_TAG} skip input delivered ({label}; no db) "
            f"client_message_id={client_message_id}",
            flush=True,
        )
        return True
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


def _wait_bootstrap_complete_flag(
    repo_root: Path,
    config_path: Path,
    *,
    user_id: str,
    agent_id: str,
    timeout_sec: float,
    stderr: TextIO,
    skip_db_checks: bool,
) -> bool:
    """Poll ``context.json`` until interactive bootstrap is marked complete."""
    assert user_id != ""
    assert agent_id != ""
    if skip_db_checks:
        print(f"{_TAG} skip bootstrap_complete flag poll (no db)", flush=True)
        return True
    scope_chat = _agent_scope_chat_id(user_id, agent_id)
    deadline = time.monotonic() + timeout_sec
    last_raw = ""
    while time.monotonic() < deadline:
        last_raw = _psql(
            repo_root,
            config_path,
            f"""
SELECT trim(content)::json->>'workspace_bootstrap_user_interactive_completed'
FROM companion_memory_document_versions
WHERE companion_id = '{agent_id}'
  AND user_id = '{user_id}'
  AND chat_id = '{scope_chat}'
  AND document_kind = 'context_json'
  AND calendar_date IS NULL
ORDER BY sequence_id DESC
LIMIT 1;
""",
        ).strip()
        if last_raw == "true":
            print(f"{_TAG} bootstrap_complete flag true", flush=True)
            return True
        time.sleep(_EXPERIENCE_PROFILE_POLL_SEC)
    print(
        f"{_TAG} ERROR timeout waiting for bootstrap_complete flag (last={last_raw!r})",
        file=stderr,
        flush=True,
    )
    return False


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
    skip_db_checks: bool,
) -> bool:
    assert expected != ""
    if skip_db_checks:
        print(
            f"{_TAG} skip context_mode poll expected={expected!r} (no db)",
            flush=True,
        )
        return True
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
    skip_db_checks: bool,
) -> BootstrapMemDocResult:
    """Check bootstrap wrote USER/IDENTITY/STYLE while SOUL/MEMORY stay at template seed."""
    if skip_db_checks:
        return BootstrapMemDocResult(
            user_customized=False,
            identity_customized=False,
            style_customized=False,
            soul_unchanged=False,
            memory_unchanged=False,
            user_sequence_id=0,
            identity_sequence_id=0,
            style_sequence_id=0,
            memory_sequence_id=0,
            errors=(),
            warnings=("skipped: no direct DB access to remote environment",),
        )
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


# TODO(dreaming-completion-notify): #3744 — replace log scraping with in-process
# completion signal once per-scope dreaming Event is wired (scope_inner_tick_state).
_DREAMING_START_LINE_RE = re.compile(
    r"dreaming_consolidation start ws=(?P<ws>\S+) rows=(?P<rows>\d+) chars=(?P<chars>\d+)"
)
_DREAMING_ONE_SHOT_START_LINE_RE = re.compile(
    r"dreaming_consolidation one_shot start ws=(?P<ws>\S+) rows=(?P<rows>\d+) "
    r"paths=(?P<paths>\d+) chars=(?P<chars>\d+)"
)
_DREAMING_CHECKPOINT_TRACE_RE = re.compile(
    r"batch_observed user=\S+ agent=(?P<agent>\S+) .*?outcome=checkpoint_saved "
    r".*?langsmith_trace_id=(?P<trace>\S+)"
)
_DREAMING_REQUIRED_PATH_RE = re.compile(r"### Current `([^`]+)`")
_DREAMING_CURATED_LINE_RE = re.compile(
    r"dreaming_consolidation curated step=(?P<step>\S+) ms=(?P<ms>\d+(?:\.\d+)?)\s+ws=(?P<ws>\S+)"
)
_DREAMING_DONE_LINE_RE = re.compile(
    r"dreaming_consolidation done total_ms=(?P<total_ms>\d+(?:\.\d+)?)\s+ws=(?P<ws>\S+)"
)


def _dreaming_registry_ws(user_id: str, agent_id: str) -> str:
    """``MemoryStore.scope.registry_key()`` value for agent-scope dreaming logs."""
    scope_chat = _agent_scope_chat_id(user_id, agent_id)
    return f"{user_id}:{agent_id}:{scope_chat}"


@dataclass
class _DreamingLogBatch:
    """Mutable accumulator while scanning one dreaming consolidation batch."""

    rows: int | None
    chars: int | None
    step_timings: list[DreamingStepTiming]
    total_curation_ms: float | None = None


def _parse_dreaming_curation_timings_from_log_text(
    log_text: str,
    *,
    user_id: str,
    agent_id: str,
) -> DreamingLogTiming | None:
    """Extract the latest scoped dreaming batch timings from backend log text."""
    assert user_id
    assert agent_id
    target_ws = _dreaming_registry_ws(user_id, agent_id)
    current: _DreamingLogBatch | None = None
    latest_complete: _DreamingLogBatch | None = None
    latest_partial: _DreamingLogBatch | None = None
    for line in log_text.splitlines():
        start_match = _DREAMING_START_LINE_RE.search(line)
        one_shot_start_match = _DREAMING_ONE_SHOT_START_LINE_RE.search(line)
        if start_match is not None or one_shot_start_match is not None:
            match = one_shot_start_match or start_match
            assert match is not None
            ws = match.group("ws")
            if ws == target_ws:
                current = _DreamingLogBatch(
                    rows=int(match.group("rows")),
                    chars=int(match.group("chars")),
                    step_timings=[],
                )
            continue
        curated_match = _DREAMING_CURATED_LINE_RE.search(line)
        if curated_match is not None:
            ws = curated_match.group("ws")
            if ws == target_ws:
                if current is None:
                    current = _DreamingLogBatch(
                        rows=None,
                        chars=None,
                        step_timings=[],
                    )
                current.step_timings.append(
                    DreamingStepTiming(
                        step=curated_match.group("step"),
                        ms=float(curated_match.group("ms")),
                    )
                )
            continue
        done_match = _DREAMING_DONE_LINE_RE.search(line)
        if done_match is not None:
            ws = done_match.group("ws")
            if ws == target_ws:
                if current is None:
                    current = _DreamingLogBatch(
                        rows=None,
                        chars=None,
                        step_timings=[],
                    )
                current.total_curation_ms = float(done_match.group("total_ms"))
                latest_complete = current
                latest_partial = current
                current = None
    if current is not None and current.step_timings:
        latest_partial = current
    chosen = latest_complete if latest_complete is not None else latest_partial
    if chosen is None:
        return None
    return DreamingLogTiming(
        step_timings=tuple(chosen.step_timings),
        total_curation_ms=chosen.total_curation_ms,
        rows=chosen.rows,
        chars=chosen.chars,
    )


def _resolve_dreaming_timing_log_paths(repo_root: Path) -> list[Path]:
    """Prefer repo-root ``.inty/inty.log``, then ``INTY_LOG_FILE`` when set."""
    paths: list[Path] = []
    inty_log = repo_root / ".inty" / "inty.log"
    if inty_log.is_file():
        paths.append(inty_log)
    env_log = os.environ.get("INTY_LOG_FILE", "").strip()
    if env_log:
        env_path = Path(env_log)
        if not env_path.is_absolute():
            env_path = repo_root / env_path
        if env_path.is_file() and env_path not in paths:
            paths.append(env_path)
    return paths


def _load_dreaming_curation_timings_from_logs(
    repo_root: Path,
    *,
    user_id: str,
    agent_id: str,
) -> DreamingLogTiming | None:
    """Load scoped dreaming step timings from Ops/backend logs."""
    for log_path in _resolve_dreaming_timing_log_paths(repo_root):
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        parsed = _parse_dreaming_curation_timings_from_log_text(
            log_text,
            user_id=user_id,
            agent_id=agent_id,
        )
        if parsed is None:
            continue
        try:
            timing_source = str(log_path.relative_to(repo_root))
        except ValueError:
            timing_source = str(log_path)
        return DreamingLogTiming(
            step_timings=parsed.step_timings,
            total_curation_ms=parsed.total_curation_ms,
            rows=parsed.rows,
            chars=parsed.chars,
            timing_source=timing_source,
        )
    return None


def _dreaming_result_with_log_timings(
    result: DreamingConsolidationResult,
    *,
    repo_root: Path,
    user_id: str,
    agent_id: str,
) -> DreamingConsolidationResult:
    """Attach parsed backend log timings to a dreaming poll result."""
    timing = _load_dreaming_curation_timings_from_logs(
        repo_root,
        user_id=user_id,
        agent_id=agent_id,
    )
    if timing is None:
        return result
    return DreamingConsolidationResult(
        checkpoint_present=result.checkpoint_present,
        memory_updated=result.memory_updated,
        memory_sequence_before=result.memory_sequence_before,
        memory_sequence_after=result.memory_sequence_after,
        error=result.error,
        log_timing=timing,
        one_shot=result.one_shot,
    )


def _langsmith_project_from_config_yaml(config_path: Path) -> str:
    """Mirror ``download_run.py`` project naming for LangSmith list_runs."""
    import getpass

    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    app_data = data.get("app") if isinstance(data.get("app"), dict) else {}
    name = str(app_data.get("name") or "inty-backend").strip() or "inty-backend"
    raw_env = app_data.get("environment", "dev")
    env_val = str(raw_env).strip().lower() if raw_env is not None else "dev"
    project = f"{name}-{env_val}"
    if env_val == "local":
        user = (os.getenv("USER") or os.getenv("USERNAME") or "").strip()
        if not user:
            try:
                user = getpass.getuser()
            except Exception:
                user = ""
        safe = "".join(
            c if c.isalnum() or c in "-_" else "-" for c in (user or "unknown")
        )
        parts = [p for p in safe.split("-") if p]
        slug = "-".join(parts) or "unknown"
        project = f"{project}-{slug}"
    return project


_DREAMING_CURATOR_MODE_ONE_SHOT = "one_shot"


def _dreaming_curator_mode_from_config_yaml(config_path: Path) -> str:
    """``agent.companion_harness.dreaming_curator_mode`` with the app default one_shot."""
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    agent = data.get("agent")
    harness = agent.get("companion_harness") if isinstance(agent, dict) else None
    if isinstance(harness, dict):
        raw = harness.get("dreaming_curator_mode")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return _DREAMING_CURATOR_MODE_ONE_SHOT


def _langchain_api_key_from_config_yaml(config_path: Path) -> str:
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    agent = data.get("agent")
    if isinstance(agent, dict):
        raw = agent.get("langchain_api_key")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    for env_name in ("LANGCHAIN_API_KEY", "LANGSMITH_API_KEY"):
        v = (os.environ.get(env_name) or "").strip()
        if v:
            return v
    raise RuntimeError("LangSmith API key missing for dreaming one-shot verify")


def _dreaming_checkpoint_langsmith_trace_id_from_logs(
    repo_root: Path,
    *,
    agent_id: str,
) -> str | None:
    """Latest ``checkpoint_saved`` LangSmith trace id for ``agent_id`` in backend logs."""
    assert agent_id
    for log_path in _resolve_dreaming_timing_log_paths(repo_root):
        if not log_path.is_file():
            continue
        trace_id: str | None = None
        for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = _DREAMING_CHECKPOINT_TRACE_RE.search(line)
            if match is None:
                continue
            if match.group("agent") != agent_id:
                continue
            trace_id = match.group("trace")
        if trace_id:
            return trace_id
    return None


def _required_paths_from_dreaming_llm_inputs(inputs: dict[str, object]) -> tuple[str, ...]:
    messages = inputs.get("messages")
    if not isinstance(messages, list):
        return ()
    for message in messages:
        if not isinstance(message, dict):
            continue
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if not isinstance(content, str):
            continue
        paths = tuple(_DREAMING_REQUIRED_PATH_RE.findall(content))
        if paths:
            return paths
    return ()


_DREAMING_ONE_SHOT_UPDATE_TOOL_NAME = "update_dreaming_document"


def _evaluate_dreaming_one_shot_tool_calls(
    tool_calls: list[Any],
    required_paths: tuple[str, ...],
    *,
    trace_id: str,
) -> DreamingOneShotVerifyResult:
    """Validate one-shot dreaming tool calls against required MemoryDoc paths."""
    assert trace_id
    by_path: dict[str, dict[str, object]] = {}
    changed_count = 0
    no_op_count = 0
    for tc in tool_calls:
        if not isinstance(tc, dict):
            continue
        fn = tc.get("function")
        if not isinstance(fn, dict):
            continue
        if fn.get("name") != _DREAMING_ONE_SHOT_UPDATE_TOOL_NAME:
            continue
        args_raw = fn.get("arguments")
        if not isinstance(args_raw, str):
            continue
        payload = json.loads(args_raw)
        if not isinstance(payload, dict):
            continue
        rel = payload.get("relative_path")
        if not isinstance(rel, str):
            continue
        if rel in by_path:
            return DreamingOneShotVerifyResult(
                ok=False,
                error=f"duplicate dreaming tool call for path {rel!r}",
                trace_id=trace_id,
                tool_call_count=len(by_path),
                required_path_count=len(required_paths),
                changed_count=changed_count,
                no_op_count=no_op_count,
                paths=tuple(sorted(by_path.keys())),
            )
        if "content_changed" not in payload:
            return DreamingOneShotVerifyResult(
                ok=False,
                error=f"tool call for {rel!r} missing content_changed",
                trace_id=trace_id,
                tool_call_count=len(by_path),
                required_path_count=len(required_paths),
                changed_count=changed_count,
                no_op_count=no_op_count,
                paths=tuple(sorted(by_path.keys())),
            )
        by_path[rel] = payload
        if bool(payload.get("content_changed")):
            changed_count += 1
        else:
            no_op_count += 1
    missing = sorted(set(required_paths) - set(by_path.keys()))
    if missing:
        return DreamingOneShotVerifyResult(
            ok=False,
            error=f"missing dreaming tool calls for paths: {missing!r}",
            trace_id=trace_id,
            tool_call_count=len(by_path),
            required_path_count=len(required_paths),
            changed_count=changed_count,
            no_op_count=no_op_count,
            paths=tuple(sorted(by_path.keys())),
        )
    extra = sorted(set(by_path.keys()) - set(required_paths))
    if extra:
        return DreamingOneShotVerifyResult(
            ok=False,
            error=f"unexpected dreaming tool call paths: {extra!r}",
            trace_id=trace_id,
            tool_call_count=len(by_path),
            required_path_count=len(required_paths),
            changed_count=changed_count,
            no_op_count=no_op_count,
            paths=tuple(sorted(by_path.keys())),
        )
    if changed_count == 0:
        return DreamingOneShotVerifyResult(
            ok=False,
            error="no content_changed=true tool calls",
            trace_id=trace_id,
            tool_call_count=len(by_path),
            required_path_count=len(required_paths),
            changed_count=0,
            no_op_count=no_op_count,
            paths=tuple(sorted(by_path.keys())),
        )
    return DreamingOneShotVerifyResult(
        ok=True,
        error=None,
        trace_id=trace_id,
        tool_call_count=len(by_path),
        required_path_count=len(required_paths),
        changed_count=changed_count,
        no_op_count=no_op_count,
        paths=tuple(sorted(by_path.keys())),
    )


def _verify_dreaming_one_shot_langsmith(
    config_path: Path,
    *,
    trace_id: str,
) -> DreamingOneShotVerifyResult:
    """Verify one-shot dreaming LLM span covers all MemoryDocs with explicit no-op support."""
    assert trace_id
    from langsmith import Client

    os.environ["LANGCHAIN_API_KEY"] = _langchain_api_key_from_config_yaml(config_path)
    project = _langsmith_project_from_config_yaml(config_path)
    client = Client(auto_batch_tracing=False)
    llm_run = None
    for run in client.list_runs(trace_id=trace_id, project_name=project, limit=50):
        if run.run_type != "llm":
            continue
        if (run.name or "").endswith("dreaming_one_shot"):
            llm_run = run
            break
    if llm_run is None:
        return DreamingOneShotVerifyResult(
            ok=False,
            error="missing LangSmith llm run dreaming_one_shot",
            trace_id=trace_id,
            tool_call_count=0,
            required_path_count=0,
            changed_count=0,
            no_op_count=0,
            paths=(),
        )
    inputs = llm_run.inputs if isinstance(llm_run.inputs, dict) else {}
    required_paths = _required_paths_from_dreaming_llm_inputs(inputs)
    outputs = llm_run.outputs if isinstance(llm_run.outputs, dict) else {}
    choices = outputs.get("choices")
    if not isinstance(choices, list) or not choices:
        return DreamingOneShotVerifyResult(
            ok=False,
            error="dreaming_one_shot llm run has no choices output",
            trace_id=trace_id,
            tool_call_count=0,
            required_path_count=len(required_paths),
            changed_count=0,
            no_op_count=0,
            paths=(),
        )
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    tool_calls = (
        message.get("tool_calls")
        if isinstance(message, dict) and isinstance(message.get("tool_calls"), list)
        else []
    )
    return _evaluate_dreaming_one_shot_tool_calls(
        tool_calls,
        required_paths,
        trace_id=trace_id,
    )


def _verify_dreaming_one_shot_for_agent(
    repo_root: Path,
    config_path: Path,
    *,
    agent_id: str,
) -> DreamingOneShotVerifyResult:
    """Resolve checkpoint trace from logs and verify one-shot tool-call coverage."""
    trace_id = _dreaming_checkpoint_langsmith_trace_id_from_logs(
        repo_root,
        agent_id=agent_id,
    )
    if not trace_id:
        return DreamingOneShotVerifyResult(
            ok=False,
            error="checkpoint_saved langsmith_trace_id not found in backend logs",
            trace_id="",
            tool_call_count=0,
            required_path_count=0,
            changed_count=0,
            no_op_count=0,
            paths=(),
        )
    return _verify_dreaming_one_shot_langsmith(config_path, trace_id=trace_id)


def _attach_dreaming_one_shot_verify(
    result: DreamingConsolidationResult,
    *,
    repo_root: Path,
    config_path: Path,
    agent_id: str,
) -> DreamingConsolidationResult:
    """LangSmith-verify one-shot tool calls when checkpoint dreaming succeeded.

    Skipped (``one_shot`` stays ``None``) when the config rolls back to the
    ``sequential`` curator mode — there is no ``dreaming_one_shot`` llm run then.
    """
    if result.error is not None or not result.checkpoint_present:
        return result
    if (
        _dreaming_curator_mode_from_config_yaml(config_path)
        != _DREAMING_CURATOR_MODE_ONE_SHOT
    ):
        return result
    one_shot = _verify_dreaming_one_shot_for_agent(
        repo_root,
        config_path,
        agent_id=agent_id,
    )
    error = result.error if one_shot.ok else one_shot.error
    return DreamingConsolidationResult(
        checkpoint_present=result.checkpoint_present,
        memory_updated=result.memory_updated,
        memory_sequence_before=result.memory_sequence_before,
        memory_sequence_after=result.memory_sequence_after,
        error=error,
        log_timing=result.log_timing,
        one_shot=one_shot,
    )


def _dreaming_report_fields(result: DreamingConsolidationResult) -> dict[str, Any]:
    """JSON-report dreaming block including optional log-derived step timings."""
    timing = result.log_timing
    fields: dict[str, Any] = {
        "checkpoint_present": result.checkpoint_present,
        "memory_updated": result.memory_updated,
        "memory_sequence_before": result.memory_sequence_before,
        "memory_sequence_after": result.memory_sequence_after,
        "error": result.error,
        "step_timings": [
            {"step": entry.step, "ms": entry.ms}
            for entry in (timing.step_timings if timing is not None else ())
        ],
        "total_curation_ms": timing.total_curation_ms if timing is not None else None,
        "rows": timing.rows if timing is not None else None,
        "chars": timing.chars if timing is not None else None,
        "timing_source": timing.timing_source if timing is not None else None,
    }
    one_shot = result.one_shot
    if one_shot is not None:
        fields["one_shot"] = {
            "ok": one_shot.ok,
            "error": one_shot.error,
            "trace_id": one_shot.trace_id,
            "tool_call_count": one_shot.tool_call_count,
            "required_path_count": one_shot.required_path_count,
            "changed_count": one_shot.changed_count,
            "no_op_count": one_shot.no_op_count,
            "paths": list(one_shot.paths),
        }
    return fields


def _summarize_dreaming_step_timings(
    step_timings: tuple[DreamingStepTiming, ...],
) -> dict[str, float]:
    """Map step name → duration ms for compact regression assertions."""
    return {entry.step: entry.ms for entry in step_timings}


def _finalize_dreaming_poll_result(
    *,
    repo_root: Path,
    config_path: Path,
    user_id: str,
    agent_id: str,
    checkpoint_present: bool,
    memory_updated: bool,
    memory_sequence_before: int,
    memory_sequence_after: int,
    error: str | None,
) -> DreamingConsolidationResult:
    """Build dreaming poll result, log timings, and LangSmith one-shot verify."""
    with_timings = _dreaming_result_with_log_timings(
        DreamingConsolidationResult(
            checkpoint_present=checkpoint_present,
            memory_updated=memory_updated,
            memory_sequence_before=memory_sequence_before,
            memory_sequence_after=memory_sequence_after,
            error=error,
        ),
        repo_root=repo_root,
        user_id=user_id,
        agent_id=agent_id,
    )
    return _attach_dreaming_one_shot_verify(
        with_timings,
        repo_root=repo_root,
        config_path=config_path,
        agent_id=agent_id,
    )


def _wait_dreaming_consolidation(
    repo_root: Path,
    config_path: Path,
    *,
    user_id: str,
    agent_id: str,
    memory_sequence_before: int,
    wait_sec: float,
    stderr: TextIO,
    skip_db_checks: bool,
) -> DreamingConsolidationResult:
    """Poll until scope dreaming checkpoint exists and MEMORY.md advances."""
    # TODO(dreaming-completion-notify): #3744 — replace Postgres MemDoc polling with
    # in-process notifier or WS completion meta; unlock immediately on signal; lower
    # local default wait_sec once notifier is wired (epic #3373).
    assert wait_sec >= 0.0
    if skip_db_checks:
        print(f"{_TAG} skip dreaming consolidation poll (no db)", flush=True)
        return _finalize_dreaming_poll_result(
            repo_root=repo_root,
            config_path=config_path,
            user_id=user_id,
            agent_id=agent_id,
            checkpoint_present=False,
            memory_updated=False,
            memory_sequence_before=memory_sequence_before,
            memory_sequence_after=memory_sequence_before,
            error=None,
        )
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
            return _finalize_dreaming_poll_result(
                repo_root=repo_root,
                config_path=config_path,
                user_id=user_id,
                agent_id=agent_id,
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
    return _finalize_dreaming_poll_result(
        repo_root=repo_root,
        config_path=config_path,
        user_id=user_id,
        agent_id=agent_id,
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
    run_started_at_utc: datetime,
    proactive_min_rounds: int,
    proactive_target_rounds: int,
    skip_db_checks: bool,
) -> dict[str, int]:
    """Merge DB proactive rows, summarize rounds, and flag legacy ``[SILENT]`` leaks."""
    if not skip_db_checks:
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
    else:
        print(f"{_TAG} skip proactive chat_history DB merge (no db)", flush=True)

    summary = _summarize_proactive_rounds(report["proactive"])
    report["proactive_summary"] = summary
    print(
        f"{_TAG} proactive summary total={summary['total']} "
        f"visible={summary['visible']} silent={summary['silent']} "
        f"min_rounds={proactive_min_rounds} target_rounds={proactive_target_rounds}",
        flush=True,
    )
    if summary["total"] < proactive_target_rounds:
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
    if summary["total"] < proactive_min_rounds and proactive_min_rounds > 0:
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


def _poll_feedback_snapshot_for_user_msg_uuid(
    repo_root: Path,
    config_path: Path,
    *,
    user_id: str,
    agent_id: str,
    user_msg_uuid: str,
    timeout_sec: float,
) -> bool:
    """Poll feedback JSONL until a snapshot row appears for the turn."""
    assert user_msg_uuid != ""
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        raw = _query_user_feedback_jsonl_content(
            repo_root,
            config_path,
            user_id=user_id,
            agent_id=agent_id,
        )
        rows = _parse_feedback_jsonl_rows(raw)
        if _find_snapshot_for_user_msg_uuid(rows, user_msg_uuid):
            return True
        time.sleep(_INPUT_QUEUE_POLL_SEC)
    return False


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
        "tool_fallback": result.tool_fallback,
        "error": result.error,
    }


def _invoke_user_feedback_tool_fallback(
    repo_root: Path,
    *,
    user_id: str,
    agent_id: str,
    user_msg_uuid: str,
    stderr: TextIO,
) -> bool:
    """Last-resort: call ``companion_record_user_feedback`` in-process when LLM skips the tool."""
    assert user_msg_uuid != ""
    _ensure_import_path(repo_root)
    import asyncio

    from app.core.companion_harness.companion.llm_runtime_events import (
        LlmRuntimeEventBind,
        companion_llm_runtime_event_bind_ctx,
    )
    from app.core.companion_harness.companion.scope import CompanionScope
    from app.core.companion_harness.memory.memory_registry import get_memory_store
    from app.core.companion_harness.tools.companion_tool_runtime import execute_tool_call
    from app.core.companion_harness.tools.companion_user_feedback import (
        COMPANION_RECORD_USER_FEEDBACK_TOOL_NAME,
    )
    from app.core.config import global_config_loaded_from_config_yaml

    scope_chat = _agent_scope_chat_id(user_id, agent_id)
    scope = CompanionScope(user_id, agent_id, scope_chat)
    dsn = (global_config_loaded_from_config_yaml.database.url or "").strip()
    assert dsn != ""
    store = get_memory_store(scope, dsn=dsn)
    bind = LlmRuntimeEventBind(
        memory_store=store,
        trace_id=f"repl-regression-fallback-{user_msg_uuid[:8]}",
        user_msg_uuid=user_msg_uuid,
        phase="tool_background",
        scene=None,
    )
    token = companion_llm_runtime_event_bind_ctx.set(bind)
    try:
        out = asyncio.run(
            execute_tool_call(
                store,
                COMPANION_RECORD_USER_FEEDBACK_TOOL_NAME,
                json.dumps(
                    {
                        "complaint_summary": (
                            "REPL regression: companion ignored timezone in weather reply"
                        ),
                        "complaint_category": "other",
                    }
                ),
            )
        )
    finally:
        companion_llm_runtime_event_bind_ctx.reset(token)
    ok = out.startswith("OK feedback_id=")
    if ok:
        print(
            f"{_TAG} github_issue in-process tool fallback ok user_msg_uuid={user_msg_uuid}",
            flush=True,
        )
    else:
        print(
            f"{_TAG} ERROR github_issue in-process tool fallback: {out}",
            file=stderr,
            flush=True,
        )
    return ok


# TODO(input-queue-lookup): #3745 — merge _query_input_status_for_client_message_id and
# _query_input_batch_id_for_client_message_id into one psql round-trip when refactoring
# github_issue E2E helpers.


# TODO(github-issue-e2e-turn-loop): #3745 — this shares most of its turn-loop / WS
# downlink wait / issue-close logic with ``_run_github_issue_e2e_phase_ws_only`` below;
# extract a common helper and keep only the DB-vs-WS-only verification branches distinct.
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
    skip_db_checks: bool,
) -> GithubIssueE2eResult:
    user_msg_uuid = ""
    issue_url = ""
    issue_number = 0
    snapshot_seen = False
    disclosed_in_chat = False
    tool_fallback = False
    error: str | None = None
    closed = False
    assistant_reply = ""

    try:
        prereq_err = _require_user_feedback_github_prereqs(stderr)
        if prereq_err is not None:
            error = prereq_err
        else:
            turn_attempts = (turn_text, _GITHUB_ISSUE_RETRY_TURN)
            for attempt_idx, current_turn in enumerate(turn_attempts):
                if attempt_idx == 1 and snapshot_seen:
                    break
                if attempt_idx == 1:
                    print(
                        f"{_TAG} github_issue retry turn: {current_turn!r}",
                        flush=True,
                    )
                else:
                    print(f"{_TAG} github_issue turn: {current_turn!r}", flush=True)
                user_msg_uuid = _send_turn(bridge, agent_id, current_turn)
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
                    break
                assert text is not None
                report["turns"].append(
                    {
                        "kind": "github_issue",
                        "user": current_turn,
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
                    skip_db_checks=skip_db_checks,
                ):
                    error = f"input not delivered: {user_msg_uuid}"
                    break
                if not _wait_ws_turn_settled(
                    bridge,
                    report,
                    label="github_issue",
                    settle_quiet_sec=_TURN_TRAILING_QUIET_SEC,
                    max_sec=_GITHUB_ISSUE_POLL_SEC,
                    stderr=stderr,
                ):
                    print(
                        f"{_TAG} warning: github_issue ws not fully quiet before "
                        "feedback poll",
                        file=stderr,
                        flush=True,
                    )
                snapshot_seen = _poll_feedback_snapshot_for_user_msg_uuid(
                    repo_root,
                    config_path,
                    user_id=user_id,
                    agent_id=agent_id,
                    user_msg_uuid=user_msg_uuid,
                    timeout_sec=_GITHUB_ISSUE_POLL_SEC,
                )
                if snapshot_seen:
                    break
                if attempt_idx + 1 >= len(turn_attempts):
                    fallback_uuid = user_msg_uuid or str(uuid.uuid4())
                    if _invoke_user_feedback_tool_fallback(
                        repo_root,
                        user_id=user_id,
                        agent_id=agent_id,
                        user_msg_uuid=fallback_uuid,
                        stderr=stderr,
                    ):
                        tool_fallback = True
                        user_msg_uuid = fallback_uuid
                        snapshot_seen = _poll_feedback_snapshot_for_user_msg_uuid(
                            repo_root,
                            config_path,
                            user_id=user_id,
                            agent_id=agent_id,
                            user_msg_uuid=user_msg_uuid,
                            timeout_sec=_GITHUB_ISSUE_POLL_SEC,
                        )
                    if not snapshot_seen:
                        error = (
                            f"no feedback snapshot for user_msg_uuid={user_msg_uuid}"
                        )
                        print(f"{_TAG} ERROR {error}", file=stderr, flush=True)
            if snapshot_seen and error is None:
                raw = _query_user_feedback_jsonl_content(
                    repo_root,
                    config_path,
                    user_id=user_id,
                    agent_id=agent_id,
                )
                rows = _parse_feedback_jsonl_rows(raw)
                feedback_id = _find_feedback_id_for_user_msg_uuid(
                    rows, user_msg_uuid
                )
                if not feedback_id:
                    error = f"no feedback_id for user_msg_uuid={user_msg_uuid}"
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
                    if tool_fallback:
                        batch_id = _query_input_batch_id_for_client_message_id(
                            repo_root,
                            config_path,
                            agent_id=agent_id,
                            client_message_id=user_msg_uuid,
                        )
                        if not batch_id:
                            error = (
                                "no input batch_id for fallback disclosure "
                                f"user_msg_uuid={user_msg_uuid}"
                            )
                            print(f"{_TAG} ERROR {error}", file=stderr, flush=True)
                        else:
                            _ensure_import_path(repo_root)
                            import asyncio

                            from app.core.companion_harness.tools.companion_user_feedback import (
                                append_user_feedback_issue_disclosure_to_output_queue,
                            )

                            disclosed = asyncio.run(
                                append_user_feedback_issue_disclosure_to_output_queue(
                                    user_id=user_id,
                                    agent_id=agent_id,
                                    batch_id=batch_id,
                                    user_msg_uuid=user_msg_uuid,
                                    issue_url=issue_url,
                                    llm_reply=assistant_reply,
                                )
                            )
                            print(
                                f"{_TAG} github_issue fallback disclosure "
                                f"appended={disclosed} user_msg_uuid={user_msg_uuid}",
                                flush=True,
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
        tool_fallback,
        error,
    )


# TODO(github-issue-e2e-turn-loop): #3745 — duplicates the turn-loop in
# ``_run_github_issue_e2e_phase`` above; see that TODO for the planned extraction.
def _run_github_issue_e2e_phase_ws_only(
    *,
    bridge: Any,
    report: dict[str, Any],
    agent_id: str,
    turn_text: str,
    stderr: TextIO,
) -> GithubIssueE2eResult:
    """WS + ``gh`` CLI github_issue phase without Postgres feedback JSONL polling."""
    user_msg_uuid = ""
    issue_url = ""
    issue_number = 0
    disclosed_in_chat = False
    error: str | None = None
    closed = False
    assistant_reply = ""

    try:
        prereq_err = _require_user_feedback_github_prereqs(stderr)
        if prereq_err is not None:
            error = prereq_err
        else:
            turn_attempts = (turn_text, _GITHUB_ISSUE_RETRY_TURN)
            for attempt_idx, current_turn in enumerate(turn_attempts):
                if attempt_idx == 1 and issue_number > 0:
                    break
                if attempt_idx == 1:
                    print(
                        f"{_TAG} github_issue ws_only retry turn: {current_turn!r}",
                        flush=True,
                    )
                else:
                    print(
                        f"{_TAG} github_issue ws_only turn: {current_turn!r}",
                        flush=True,
                    )
                user_msg_uuid = _send_turn(bridge, agent_id, current_turn)
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
                    break
                assert text is not None
                report["turns"].append(
                    {
                        "kind": "github_issue",
                        "user": current_turn,
                        "user_msg_uuid": user_msg_uuid,
                        "text_preview": text[:120],
                        "meta": meta,
                    }
                )
                assistant_reply = text + _drain_turn_trailing_frames(
                    bridge, report, label="github_issue"
                )
                for extra_text, extra_meta in _drain_until_quiet(
                    bridge,
                    quiet_sec=_TURN_TRAILING_QUIET_SEC,
                    max_sec=_GITHUB_ISSUE_POLL_SEC,
                ):
                    assistant_reply += extra_text
                    _record_trailing_downlink(
                        report,
                        label="github_issue_ws_drain",
                        text=extra_text,
                        meta=extra_meta,
                    )
                issue_url, issue_number = _extract_github_issue_url(assistant_reply)
                if issue_number > 0:
                    break
            if issue_number <= 0 and error is None:
                error = "no GitHub issue URL disclosed in chat"
                print(f"{_TAG} ERROR {error}", file=stderr, flush=True)
            if issue_number > 0 and error is None:
                issue_row = FeedbackGithubIssueRow(
                    issue_url=issue_url,
                    issue_number=issue_number,
                    user_msg_uuid=user_msg_uuid,
                    feedback_id="",
                )
                _verify_github_issue_via_gh(
                    issue_row,
                    expected_user_msg_uuid=user_msg_uuid,
                )
                disclosed_in_chat = _assistant_reply_discloses_issue_url(
                    assistant_reply,
                    issue_url,
                    issue_number,
                )
                print(
                    f"{_TAG} github_issue ws_only verified issue=#{issue_number} "
                    f"url={issue_url} disclosed_in_chat={disclosed_in_chat}",
                    flush=True,
                )
    except (RuntimeError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
        error = str(exc)
        print(f"{_TAG} ERROR github_issue_e2e_ws_only: {error}", file=stderr, flush=True)
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
        issue_number > 0,
        closed,
        disclosed_in_chat,
        False,
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
    skip_db_checks: bool,
) -> bool:
    """Drive one USER_CHAT_BOOTSTRAP/settled turn that must call ``companion_set_experience_profile``."""
    _wait_phase_infra_settled(
        bridge=bridge,
        report=report,
        repo_root=repo_root,
        config_path=config_path,
        agent_id=agent_id,
        stderr=stderr,
        spec=PhaseSettleSpec(
            label="pre-experience_profile",
            ws_quiet_sec=_BOOTSTRAP_TURN_SETTLE_QUIET_SEC,
            ws_max_sec=_BOOTSTRAP_TURN_SETTLE_MAX_SEC,
            wait_input_queue=True,
            wait_output_queue=True,
            queue_timeout_sec=_BOOTSTRAP_TURN_SETTLE_MAX_SEC,
            input_queue_timeout_sec=_TURN_REPLY_TIMEOUT_SEC,
        ),
        skip_db_checks=skip_db_checks,
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
        skip_db_checks=skip_db_checks,
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
        skip_db_checks=skip_db_checks,
    )
    report["experience_profile"] = {
        "expected_context_mode": experience_profile_context_mode,
        "matched": matched,
        "actual_context_mode": (
            "skipped"
            if skip_db_checks
            else _query_context_mode(
                repo_root,
                config_path,
                user_id=user_id,
                agent_id=agent_id,
            )
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
    _wait_phase_infra_settled(
        bridge=bridge,
        report=report,
        repo_root=repo_root,
        config_path=config_path,
        agent_id=agent_id,
        stderr=stderr,
        spec=PhaseSettleSpec(
            label="experience_profile_post",
            ws_quiet_sec=_BOOTSTRAP_TURN_SETTLE_QUIET_SEC,
            ws_max_sec=_BOOTSTRAP_TURN_SETTLE_MAX_SEC,
            wait_input_queue=False,
            wait_output_queue=True,
            queue_timeout_sec=_BOOTSTRAP_TURN_SETTLE_MAX_SEC,
        ),
        skip_db_checks=skip_db_checks,
    )
    return matched


# TODO(regression-summary-args): #3746 — 20+ keyword args exceed the repo's "group into
# dataclass past 3-5 args" style rule; split into per-phase frozen dataclasses.
def _build_regression_summary(
    *,
    bootstrap_done: str,
    context_mode: str,
    greeting_result: ImplicitSignOnGreetingResult,
    memdoc_result: BootstrapMemDocResult,
    experience_profile_ok: bool,
    dreaming_result: DreamingConsolidationResult,
    github_result: GithubIssueE2eResult,
    app_debug: bool,
    settled_ok: bool,
    report_errors: list[Any],
    proactive_summary: dict[str, int],
    proactive_target_met: bool,
    proactive_present: bool,
    proactive_silent_ok: bool,
    in_q: str,
    out_q: str,
    in_all_delivered: bool,
    output_user_visible_delivered: bool,
    companion_bond_state: str,
    skip_db_checks: bool,
    scope: RegressionScope,
    proactive_min_rounds: int,
) -> tuple[dict[str, Any], InfraPassGate, EvalTelemetry]:
    """Compute JSON summary, infra pass gate, and L1 eval telemetry from phase results."""
    github_pipeline_ok = github_result.error is None and github_result.closed
    infra_gate = InfraPassGate(
        bootstrap_done=bootstrap_done == "true",
        greeting_present=greeting_result.present,
        memdoc_errors=memdoc_result.errors,
        experience_profile_ok=experience_profile_ok,
        dreaming_ok=dreaming_result.error is None,
        settled_ok=settled_ok,
        has_report_errors=bool(report_errors),
        input_all_delivered=in_all_delivered,
        output_user_visible_delivered=output_user_visible_delivered,
        github_pipeline_ok=github_pipeline_ok,
        proactive_present=proactive_present,
        proactive_silent_ok=proactive_silent_ok,
        scope=scope,
        skip_db_checks=skip_db_checks,
        proactive_min_rounds=proactive_min_rounds,
    )
    one_shot_ok = (
        None
        if skip_db_checks or dreaming_result.one_shot is None
        else dreaming_result.one_shot.ok
    )
    eval_telemetry = EvalTelemetry(
        github_tool_native=not github_result.tool_fallback,
        github_disclosed_in_chat=github_result.disclosed_in_chat,
        proactive_target_met=proactive_target_met,
        proactive_visible_rounds=proactive_summary["visible"],
        proactive_silent_rounds=proactive_summary["silent"],
        dreaming_one_shot_ok=one_shot_ok,
    )
    memdoc_status = (
        RegressionCheckStatus.SKIPPED.value
        if skip_db_checks
        else (
            RegressionCheckStatus.PASS.value
            if not memdoc_result.errors
            else RegressionCheckStatus.FAIL.value
        )
    )
    dreaming_status = (
        RegressionCheckStatus.SKIPPED.value
        if skip_db_checks
        else (
            RegressionCheckStatus.PASS.value
            if infra_gate.dreaming_ok
            else RegressionCheckStatus.FAIL.value
        )
    )
    input_delivery_status = (
        RegressionCheckStatus.SKIPPED.value
        if skip_db_checks
        else (
            RegressionCheckStatus.PASS.value
            if in_all_delivered
            else RegressionCheckStatus.FAIL.value
        )
    )
    output_delivery_status = (
        RegressionCheckStatus.SKIPPED.value
        if skip_db_checks
        else (
            RegressionCheckStatus.PASS.value
            if output_user_visible_delivered
            else RegressionCheckStatus.FAIL.value
        )
    )
    if scope == RegressionScope.SAFE_SUBSET:
        disclosure_eval = RegressionCheckStatus.SKIPPED.value
    elif not app_debug:
        disclosure_eval = RegressionCheckStatus.SKIPPED.value
    elif github_pipeline_ok and github_result.disclosed_in_chat:
        disclosure_eval = RegressionCheckStatus.PASS.value
    elif github_pipeline_ok:
        disclosure_eval = RegressionCheckStatus.FAIL.value
    else:
        disclosure_eval = RegressionCheckStatus.SKIPPED.value
    if scope == RegressionScope.SAFE_SUBSET or proactive_min_rounds == 0:
        proactive_target_eval = RegressionCheckStatus.SKIPPED.value
    else:
        proactive_target_eval = "met" if proactive_target_met else "miss"
    if skip_db_checks or dreaming_result.one_shot is None:
        dreaming_one_shot_eval = RegressionCheckStatus.SKIPPED.value
    elif dreaming_result.one_shot.ok:
        dreaming_one_shot_eval = RegressionCheckStatus.PASS.value
    else:
        dreaming_one_shot_eval = RegressionCheckStatus.FAIL.value
    summary = {
        "target_scope": scope.value,
        "db_checks": (
            RegressionCheckStatus.SKIPPED.value
            if skip_db_checks
            else RegressionCheckStatus.PASS.value
        ),
        "bootstrap": "complete" if infra_gate.bootstrap_done else "incomplete",
        "context_mode": context_mode,
        "implicit_sign_on_greeting": (
            RegressionCheckStatus.PASS.value
            if greeting_result.present
            else RegressionCheckStatus.FAIL.value
        ),
        "bootstrap_memdocs": memdoc_status,
        "experience_profile": (
            RegressionCheckStatus.SKIPPED.value
            if scope == RegressionScope.SAFE_SUBSET
            else (
                RegressionCheckStatus.PASS.value
                if experience_profile_ok
                else RegressionCheckStatus.FAIL.value
            )
        ),
        "dreaming_consolidation": dreaming_status,
        "settled_queue_turn": (
            RegressionCheckStatus.PASS.value
            if settled_ok and not report_errors
            else RegressionCheckStatus.FAIL.value
        ),
        "github_issue_e2e": (
            RegressionCheckStatus.SKIPPED.value
            if scope == RegressionScope.SAFE_SUBSET
            else (
                RegressionCheckStatus.PASS.value
                if github_pipeline_ok
                else RegressionCheckStatus.FAIL.value
            )
        ),
        "proactive_inner_tick": (
            RegressionCheckStatus.SKIPPED.value
            if scope == RegressionScope.SAFE_SUBSET or proactive_min_rounds == 0
            else ("present" if proactive_present else "missing")
        ),
        "proactive_no_silent_token": (
            RegressionCheckStatus.SKIPPED.value
            if scope == RegressionScope.SAFE_SUBSET or proactive_min_rounds == 0
            else (
                RegressionCheckStatus.PASS.value
                if proactive_silent_ok
                else RegressionCheckStatus.FAIL.value
            )
        ),
        "companion_bond_state": companion_bond_state or "missing",
        "input_queue_counts": in_q.strip(),
        "output_queue_counts": out_q.strip(),
        "input_all_delivered": input_delivery_status,
        "output_user_visible_delivered": output_delivery_status,
        "eval": {
            "github_tool_native": eval_telemetry.github_tool_native,
            "github_issue_disclosed_in_chat": disclosure_eval,
            "proactive_target_rounds": proactive_target_eval,
            "dreaming_one_shot": dreaming_one_shot_eval,
            "proactive_visible_rounds": eval_telemetry.proactive_visible_rounds,
            "proactive_silent_rounds": eval_telemetry.proactive_silent_rounds,
        },
    }
    return summary, infra_gate, eval_telemetry


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
    skip_db_checks: bool,
    scope: RegressionScope,
) -> int:
    os.environ["INTY_CONFIG_YAML"] = str(config_path.resolve())
    app_debug = _load_app_debug_from_config(config_path)
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
        "target_scope": scope.value,
        "skip_db_checks": skip_db_checks,
        "turns": [],
        "proactive": [],
        "errors": [],
        "github_issue": {},
        "greeting": {},
        "bootstrap_memdocs": {},
        "experience_profile": {},
        "dreaming": {},
        "db": {},
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
    bootstrap_complete_flag = False
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

        if scope == RegressionScope.SAFE_SUBSET:
            print(f"{_TAG} safe_subset settled turn: {settled_turn!r}", flush=True)
            settled_msg_uuid = _send_turn(bridge, agent_id, settled_turn)
            text, meta, err = _wait_downlink_for_user_msg_uuid(
                bridge,
                report,
                expected_user_msg_uuid=settled_msg_uuid,
                timeout_sec=_SETTLED_TURN_TIMEOUT_SEC,
                label="safe_subset_settled",
                trailing_label="safe_subset_settled_mismatch",
            )
            if err is not None:
                report["errors"].append({"turn": "safe_subset_settled", "error": err})
                print(
                    f"{_TAG} ERROR safe_subset_settled: {err}",
                    file=stderr,
                    flush=True,
                )
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
                    f"{_TAG} safe_subset settled reply={text[:80]!r} "
                    f"user_msg_uuid={settled_msg_uuid}",
                    flush=True,
                )
                _drain_turn_trailing_frames(
                    bridge, report, label="safe_subset_settled"
                )

        if scope == RegressionScope.FULL:
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
                    skip_db_checks=skip_db_checks,
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
                skip_db_checks=skip_db_checks,
            )

            print(f"{_TAG} bootstrap finish turn: {bootstrap_finish_turn!r}", flush=True)
            bootstrap_finish_msg_uuid = _send_turn(bridge, agent_id, bootstrap_finish_turn)
            text, meta, err = _wait_downlink_for_user_msg_uuid(
                bridge,
                report,
                expected_user_msg_uuid=bootstrap_finish_msg_uuid,
                timeout_sec=_BOOTSTRAP_TURN_SETTLE_MAX_SEC,
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
            if not _wait_input_delivered(
                repo_root,
                config_path,
                agent_id=agent_id,
                client_message_id=bootstrap_finish_msg_uuid,
                timeout_sec=_BOOTSTRAP_TURN_SETTLE_MAX_SEC,
                label="bootstrap-finish",
                stderr=stderr,
                skip_db_checks=skip_db_checks,
            ):
                report["errors"].append(
                    {
                        "turn": "bootstrap-finish-delivered",
                        "error": (
                            408,
                            f"input not delivered: {bootstrap_finish_msg_uuid}",
                        ),
                    }
                )
            bootstrap_complete_flag = _wait_bootstrap_complete_flag(
                repo_root,
                config_path,
                user_id=user_id,
                agent_id=agent_id,
                timeout_sec=_BOOTSTRAP_TURN_SETTLE_MAX_SEC,
                stderr=stderr,
                skip_db_checks=skip_db_checks,
            )
            if not bootstrap_complete_flag:
                report["errors"].append(
                    {
                        "turn": "bootstrap-finish",
                        "error": (422, "bootstrap_complete flag still false"),
                    }
                )

            if not _wait_input_queue_idle(
                repo_root,
                config_path,
                agent_id=agent_id,
                timeout_sec=_TURN_REPLY_TIMEOUT_SEC,
                label="pre-settled",
                stderr=stderr,
                skip_db_checks=skip_db_checks,
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
                    skip_db_checks=skip_db_checks,
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

            print(f"{_TAG} settled turn: {settled_turn!r}", flush=True)
            settled_msg_uuid = _send_turn(bridge, agent_id, settled_turn)

            if not _wait_input_delivered(
                repo_root,
                config_path,
                agent_id=agent_id,
                client_message_id=settled_msg_uuid,
                timeout_sec=_SETTLED_TURN_TIMEOUT_SEC,
                label="settled",
                stderr=stderr,
                skip_db_checks=skip_db_checks,
            ):
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
                    False,
                    "skipped: settled input not delivered",
                )
                report["github_issue"] = _github_issue_e2e_result_to_report(
                    github_result
                )
            else:
                text, meta, err = _wait_downlink_for_user_msg_uuid(
                    bridge,
                    report,
                    expected_user_msg_uuid=settled_msg_uuid,
                    timeout_sec=_SETTLED_TURN_TIMEOUT_SEC,
                    label="settled",
                    trailing_label="settled_mismatch",
                )
                if err is not None:
                    report["errors"].append({"turn": "settled", "error": err})
                    print(f"{_TAG} ERROR settled: {err}", file=stderr, flush=True)
                    github_result = GithubIssueE2eResult(
                        "",
                        "",
                        0,
                        False,
                        False,
                        False,
                        False,
                        "skipped: settled downlink failed",
                    )
                    report["github_issue"] = _github_issue_e2e_result_to_report(
                        github_result
                    )
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
                    if skip_db_checks:
                        github_result = _run_github_issue_e2e_phase_ws_only(
                            bridge=bridge,
                            report=report,
                            agent_id=agent_id,
                            turn_text=_DEFAULT_GITHUB_ISSUE_TURN,
                            stderr=stderr,
                        )
                    else:
                        github_result = _run_github_issue_e2e_phase(
                            bridge=bridge,
                            report=report,
                            repo_root=repo_root,
                            config_path=config_path,
                            agent_id=agent_id,
                            user_id=user_id,
                            turn_text=_DEFAULT_GITHUB_ISSUE_TURN,
                            stderr=stderr,
                            skip_db_checks=skip_db_checks,
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
                    proactive_db_early_exit = (
                        not skip_db_checks and proactive_min_rounds > 0
                    )
                    while time.monotonic() < proactive_deadline:
                        if proactive_db_early_exit:
                            proactive_rows = _query_proactive_chat_history_rows(
                                repo_root,
                                config_path,
                                user_id=user_id,
                                agent_id=agent_id,
                                run_started_at_utc=run_started_at_utc,
                            )
                            if _proactive_early_exit_ready(
                                len(proactive_rows),
                                proactive_min_rounds,
                            ):
                                print(
                                    f"{_TAG} proactive early exit: "
                                    f"db_rows={len(proactive_rows)} "
                                    f">= min_rounds={proactive_min_rounds}",
                                    flush=True,
                                )
                                break
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
                    # TODO(dreaming-completion-notify): #3744 — keep WS open through dreaming
                    # or subscribe to in-process notifier; avoid disconnect-then-DB-poll.
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
                        skip_db_checks=skip_db_checks,
                    )
                    report["dreaming"] = _dreaming_report_fields(dreaming_result)
                    if dreaming_result.one_shot is not None and dreaming_result.one_shot.ok:
                        os_ = dreaming_result.one_shot
                        print(
                            f"{_TAG} dreaming one_shot verified "
                            f"tool_calls={os_.tool_call_count} "
                            f"changed={os_.changed_count} no_op={os_.no_op_count} "
                            f"trace_id={os_.trace_id}",
                            flush=True,
                        )
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
    if skip_db_checks:
        print(f"{_TAG} skip final Postgres summary block (no db)", flush=True)
        ctx_rows = ""
        in_q = ""
        out_q = ""
        out_latest = ""
        bootstrap_done = "true" if bootstrap_complete_flag else "unknown"
        context_mode = "unknown"
        companion_bond_state = None
    else:
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
        ctx_line = ctx_rows.strip().split("\n")[0] if ctx_rows.strip() else ""
        parts = ctx_line.split("|") if ctx_line else []
        bootstrap_done = parts[2] if len(parts) >= 3 else "unknown"
        context_mode = parts[1] if len(parts) >= 2 else "unknown"
        companion_bond_state = _query_active_companion_bond_agent_id(
            repo_root,
            config_path,
            user_id=user_id,
            agent_id=agent_id,
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
        skip_db_checks=skip_db_checks,
    )

    proactive_present = (
        proactive_min_rounds == 0
        or proactive_summary["total"] >= proactive_min_rounds
    )
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
    if skip_db_checks:
        output_user_visible_delivered = True
    else:
        output_delivery_rows = _query_output_delivery_rows(
            repo_root,
            config_path,
            agent_id=agent_id,
        )
        output_user_visible_delivered = _output_user_visible_delivered(
            output_delivery_rows
        )

    report["companion_bond"] = {
        "user_id": user_id,
        "agent_id": agent_id,
        "state": companion_bond_state,
    }

    summary, infra_gate, eval_telemetry = _build_regression_summary(
        bootstrap_done=bootstrap_done,
        context_mode=context_mode,
        greeting_result=greeting_result,
        memdoc_result=memdoc_result,
        experience_profile_ok=experience_profile_ok,
        dreaming_result=dreaming_result,
        github_result=github_result,
        app_debug=app_debug,
        settled_ok=settled_ok,
        report_errors=report["errors"],
        proactive_summary=proactive_summary,
        proactive_target_met=proactive_target_met,
        proactive_present=proactive_present,
        proactive_silent_ok=proactive_silent_ok,
        in_q=in_q,
        out_q=out_q,
        in_all_delivered=in_all_delivered,
        output_user_visible_delivered=output_user_visible_delivered,
        companion_bond_state=companion_bond_state or "",
        skip_db_checks=skip_db_checks,
        scope=scope,
        proactive_min_rounds=proactive_min_rounds,
    )
    report["summary"] = summary
    report["eval_telemetry"] = {
        "github_tool_native": eval_telemetry.github_tool_native,
        "github_disclosed_in_chat": eval_telemetry.github_disclosed_in_chat,
        "proactive_target_met": eval_telemetry.proactive_target_met,
        "proactive_visible_rounds": eval_telemetry.proactive_visible_rounds,
        "proactive_silent_rounds": eval_telemetry.proactive_silent_rounds,
        "dreaming_one_shot_ok": eval_telemetry.dreaming_one_shot_ok,
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"{_TAG} report written to {report_path}", flush=True)
    print(
        f"{_TAG} SUMMARY: {json.dumps(summary, ensure_ascii=False)} "
        f"eval={json.dumps(summary.get('eval', {}), ensure_ascii=False)}",
        flush=True,
    )

    return 0 if infra_gate.passed() else 1


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
        description="Automated Ops WebSocket regression for companion queue-serving.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_format_target_preset_table(repo_root),
    )
    p.add_argument(
        "--target",
        required=True,
        choices=[RegressionTarget.LOCAL.value, RegressionTarget.DEV.value, RegressionTarget.PROD.value],
        help="Deployment target preset (required)",
    )
    p.add_argument(
        "--login-email",
        default="",
        help="Login email to obtain bearer token via /api/v1/auth/google/login",
    )
    p.add_argument(
        "--login-password",
        default="",
        help="Login password (pair with --login-email)",
    )
    p.add_argument(
        "--agent-id",
        default="",
        help="Existing bootstrap test agent id (required unless --create-agent)",
    )
    p.add_argument(
        "--create-agent",
        action="store_true",
        help=(
            "POST a fresh PRIVATE agent before the regression run; on dev/prod also "
            "DELETE owned bootstrap-test-* agents first (server deactivates bond)"
        ),
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
    target = RegressionTarget(str(args.target).strip())
    preset = _target_presets(target, repo_root)
    os.environ["INTY_CONFIG_YAML"] = preset.config_path
    print(
        f"{_TAG} INTY_CONFIG_YAML={preset.config_path} "
        f"(start Ops with: export INTY_CONFIG_YAML={preset.config_path} "
        f"&& backend/ops/start.sh --local --no-build-frontend)",
        flush=True,
    )

    api_base = str(args.api_base).strip()
    if api_base == default_api:
        api_base = preset.api_base
    config_raw = str(args.config).strip()
    if config_raw == default_config or config_raw == _DEFAULT_CONFIG:
        config_path = repo_root / preset.config_path
    else:
        config_path = Path(config_raw)
        if not config_path.is_absolute():
            config_path = repo_root / config_path
    if not config_path.is_file():
        print(f"error: config not found: {config_path}", file=sys.stderr)
        return 2

    login_email = str(args.login_email).strip()
    login_password = str(args.login_password).strip()
    token_path = Path(str(args.token_file).strip())
    if not token_path.is_absolute():
        token_path = repo_root / token_path
    if login_email or login_password:
        if not login_email or not login_password:
            print(
                "error: --login-email and --login-password must be used together",
                file=sys.stderr,
            )
            return 2
        _login_and_cache_bearer_token(
            api_base=api_base,
            email=login_email,
            password=login_password,
            token_path=token_path,
        )

    proactive_min_rounds = int(args.proactive_min_rounds)
    if proactive_min_rounds == _DEFAULT_PROACTIVE_MIN_ROUNDS and (
        str(args.config).strip() == default_config
        or str(args.config).strip() == _DEFAULT_CONFIG
    ):
        proactive_min_rounds = preset.proactive_min_rounds_default

    agent_id = str(args.agent_id).strip()
    if args.create_agent:
        if agent_id:
            print(
                f"{_TAG} warning: --agent-id ignored when --create-agent is set",
                file=sys.stderr,
            )
        if not preset.skip_db_checks:
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
        else:
            purged = _purge_regression_bootstrap_agents_via_api(
                api_base=api_base,
                token_path=str(token_path),
                http_timeout=float(args.create_timeout),
                stderr=sys.stderr,
            )
            print(
                f"{_TAG} purged {purged} bootstrap-test agent(s) via API",
                file=sys.stderr,
            )
        agent_id = _create_agent_id(
            repo_root=repo_root,
            api_base=api_base,
            token_path=str(token_path),
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
    if proactive_min_rounds < 0:
        print("error: --proactive-min-rounds must be >= 0", file=sys.stderr)
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
        api_base=api_base,
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
        token_path=str(token_path),
        stderr=sys.stderr,
        skip_db_checks=preset.skip_db_checks,
        scope=preset.scope,
    )


if __name__ == "__main__":
    raise SystemExit(main())
