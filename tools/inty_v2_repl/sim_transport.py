"""Shared WebSocket transport, Postgres queue helpers, and target presets for REPL drivers.

Extracted from ``run_inty_repl_regression.py`` so ``inty_user_sim`` and regression share
the same app-ws turn/drain/queue primitives without importing ``.cursor/skills/scripts/``.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, TextIO

import yaml

from app.schemas.chat import UserTimeContext

RECV_POLL_SEC = 0.25
INPUT_QUEUE_POLL_SEC = 0.5
TURN_REPLY_TIMEOUT_SEC = 180.0
TURN_TRAILING_QUIET_SEC = 5.0
BOOTSTRAP_TURN_SETTLE_QUIET_SEC = 8.0
BOOTSTRAP_TURN_SETTLE_MAX_SEC = 300.0
EXPERIENCE_PROFILE_POLL_SEC = 2.0
INNER_TICK_SKIPPED_BATCH_PREFIX = "agent-initiated:inner_tick"
TRANSPORT_TAG = "[sim-transport]"

DEFAULT_API_BASE = "http://127.0.0.1:8001"
DEFAULT_CONFIG = "devops/config.yaml.regression_tests"
DEFAULT_USER_ID = "user-testing"
DEV_API_BASE = "https://dev.ops.inty.cc"
PROD_API_BASE = "https://ops.inty.cc"
DEV_CONFIG = "devops/config.yaml.dev"
PROD_CONFIG = "devops/config.yaml.prod"
DEFAULT_PROACTIVE_MIN_ROUNDS = 1


class RegressionTarget(StrEnum):
    """Deployment endpoint selected by ``--target`` on REPL regression and user sim."""

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


class DeliveryQueueKind(StrEnum):
    """Companion durable queue polled during settle waits."""

    INPUT = "input"
    OUTPUT = "output"


@dataclass(frozen=True)
class MemDocVersion:
    """Latest MemoryStore document row snapshot for one agent-scope MemDoc."""

    sequence_id: int
    content: str


@dataclass(frozen=True)
class TurnDrainResult:
    """Outcome of one user turn over app-ws including queue delivery."""

    user_msg_uuid: str
    assistant_text: str | None
    meta: dict[str, Any]
    input_queue_status: str
    memdoc_user_seq: int | None
    error: tuple[int, str] | None


def target_presets(target: RegressionTarget, repo_root: Path) -> TargetPreset:
    """Single source of truth for per-target api_base, config, DB mode, and scope."""
    assert repo_root.is_dir()
    match target:
        case RegressionTarget.LOCAL:
            return TargetPreset(
                api_base=DEFAULT_API_BASE,
                config_path=DEFAULT_CONFIG,
                skip_db_checks=False,
                scope=RegressionScope.FULL,
                proactive_min_rounds_default=DEFAULT_PROACTIVE_MIN_ROUNDS,
                db_checks_label="Postgres verified",
                turn_scope_label="Full regression",
            )
        case RegressionTarget.DEV:
            return TargetPreset(
                api_base=DEV_API_BASE,
                config_path=DEV_CONFIG,
                skip_db_checks=True,
                scope=RegressionScope.FULL,
                proactive_min_rounds_default=0,
                db_checks_label="WS + gh only (no direct Postgres)",
                turn_scope_label="Full regression",
            )
        case RegressionTarget.PROD:
            return TargetPreset(
                api_base=PROD_API_BASE,
                config_path=PROD_CONFIG,
                skip_db_checks=True,
                scope=RegressionScope.SAFE_SUBSET,
                proactive_min_rounds_default=0,
                db_checks_label="WS only",
                turn_scope_label="Safe subset: greeting + one settled turn",
            )


def format_target_preset_table(repo_root: Path) -> str:
    """Render the ``--target`` preset table for CLI epilog."""
    assert repo_root.is_dir()
    rows: list[tuple[str, str, str, str, str]] = []
    for target in RegressionTarget:
        preset = target_presets(target, repo_root)
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
        "--target presets (from target_presets; same values used at runtime):\n\n"
        f"{header_line}\n"
        + "\n".join(body_lines)
    )


def find_repo_root(start: Path | None = None) -> Path:
    """Walk parents from ``start`` (or this file) to locate the Inty repo root."""
    here = (start or Path(__file__)).resolve()
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


def ensure_import_path(repo_root: Path) -> None:
    root_s = str(repo_root)
    if root_s not in sys.path:
        sys.path.insert(0, root_s)


def read_bearer(repo_root: Path, token_path: str) -> str:
    p = Path(token_path)
    if not p.is_absolute():
        p = repo_root / p
    tok = p.read_text(encoding="utf-8").strip()
    assert tok != ""
    return tok


def psql(repo_root: Path, config_path: Path, query: str) -> str:
    """Run one read query against Postgres credentials from Inty config YAML."""
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


def agent_scope_chat_id(user_id: str, agent_id: str) -> str:
    assert user_id != ""
    assert agent_id != ""
    return f"agent-scope:{user_id}:{agent_id}"


def send_turn(
    bridge: Any,
    agent_id: str,
    text: str,
    *,
    user_time_context: UserTimeContext | None = None,
) -> str:
    """Fire-and-forget one user turn; return client ``message_id``."""
    msg_uuid = str(uuid.uuid4())
    bridge.post_turn(
        agent_id,
        text,
        msg_uuid,
        user_time_context=user_time_context,
    )
    return msg_uuid


def wait_downlink(
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
        time.sleep(RECV_POLL_SEC)
    return None, {}, (408, f"timeout waiting for {label}")


def drain_until_quiet(
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
            time.sleep(RECV_POLL_SEC)
    return out


def downlink_user_msg_uuid(meta: dict[str, Any]) -> str:
    return str(meta.get("user_msg_uuid") or "").strip()


def wait_downlink_for_user_msg_uuid(
    bridge: Any,
    *,
    expected_user_msg_uuid: str,
    timeout_sec: float,
    label: str,
) -> tuple[str | None, dict[str, Any], tuple[int, str] | None]:
    """Accept only a WS downlink whose ``user_msg_uuid`` matches the sent turn."""
    assert expected_user_msg_uuid != ""
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        text, err, meta = bridge.try_pop_queued_chat()
        if err is not None:
            return None, {}, err
        if text is None:
            time.sleep(RECV_POLL_SEC)
            continue
        actual = downlink_user_msg_uuid(meta)
        if actual == expected_user_msg_uuid:
            return text, meta, None
        time.sleep(RECV_POLL_SEC)
    return (
        None,
        {},
        (408, f"timeout waiting for {label} user_msg_uuid={expected_user_msg_uuid}"),
    )


def parse_input_queue_status_counts(raw: str) -> dict[str, int]:
    """Parse ``status|count`` lines from InputQueue GROUP BY query."""
    counts: dict[str, int] = {}
    for line in raw.strip().splitlines():
        if not line.strip():
            continue
        status, count_s = line.split("|", 1)
        counts[status] = int(count_s)
    return counts


def delivery_queue_table(kind: DeliveryQueueKind) -> str:
    match kind:
        case DeliveryQueueKind.INPUT:
            return "agentic_companion_input_queue"
        case DeliveryQueueKind.OUTPUT:
            return "agentic_companion_output_queue"


def queue_has_in_flight(counts: dict[str, int]) -> bool:
    return counts.get("pending", 0) > 0 or counts.get("claimed", 0) > 0


def query_queue_status_counts(
    repo_root: Path,
    config_path: Path,
    *,
    kind: DeliveryQueueKind,
    agent_id: str,
) -> dict[str, int]:
    assert agent_id != ""
    table = delivery_queue_table(kind)
    raw = psql(
        repo_root,
        config_path,
        f"SELECT status, COUNT(*) FROM {table} "
        f"WHERE agent_id = '{agent_id}' GROUP BY status ORDER BY status;",
    )
    return parse_input_queue_status_counts(raw)


def wait_queue_idle(
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
            f"{TRANSPORT_TAG} skip {kind.value} queue idle ({label}; no db)",
            flush=True,
        )
        return True
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        counts = query_queue_status_counts(
            repo_root,
            config_path,
            kind=kind,
            agent_id=agent_id,
        )
        if not queue_has_in_flight(counts):
            print(
                f"{TRANSPORT_TAG} {kind.value} queue idle ({label}) counts={counts}",
                flush=True,
            )
            return True
        time.sleep(INPUT_QUEUE_POLL_SEC)
    counts = query_queue_status_counts(
        repo_root, config_path, kind=kind, agent_id=agent_id
    )
    print(
        f"{TRANSPORT_TAG} ERROR timeout waiting for {kind.value} queue idle ({label}) "
        f"counts={counts}",
        file=stderr,
        flush=True,
    )
    return False


def wait_input_queue_idle(
    repo_root: Path,
    config_path: Path,
    *,
    agent_id: str,
    timeout_sec: float,
    label: str,
    stderr: TextIO,
    skip_db_checks: bool,
) -> bool:
    return wait_queue_idle(
        repo_root,
        config_path,
        kind=DeliveryQueueKind.INPUT,
        agent_id=agent_id,
        timeout_sec=timeout_sec,
        label=label,
        stderr=stderr,
        skip_db_checks=skip_db_checks,
    )


def wait_output_queue_idle(
    repo_root: Path,
    config_path: Path,
    *,
    agent_id: str,
    timeout_sec: float,
    label: str,
    stderr: TextIO,
    skip_db_checks: bool,
) -> bool:
    return wait_queue_idle(
        repo_root,
        config_path,
        kind=DeliveryQueueKind.OUTPUT,
        agent_id=agent_id,
        timeout_sec=timeout_sec,
        label=label,
        stderr=stderr,
        skip_db_checks=skip_db_checks,
    )


def query_input_status_for_client_message_id(
    repo_root: Path,
    config_path: Path,
    *,
    agent_id: str,
    client_message_id: str,
) -> str:
    assert agent_id != ""
    assert client_message_id != ""
    return psql(
        repo_root,
        config_path,
        "SELECT status FROM agentic_companion_input_queue "
        f"WHERE agent_id = '{agent_id}' "
        f"AND client_message_id = '{client_message_id}' "
        "ORDER BY sequence_id DESC LIMIT 1;",
    ).strip()


def wait_input_delivered(
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
        return True
    deadline = time.monotonic() + timeout_sec
    status = ""
    while time.monotonic() < deadline:
        status = query_input_status_for_client_message_id(
            repo_root,
            config_path,
            agent_id=agent_id,
            client_message_id=client_message_id,
        )
        match status:
            case "delivered":
                return True
            case "failed":
                print(
                    f"{TRANSPORT_TAG} ERROR input failed ({label}) "
                    f"client_message_id={client_message_id}",
                    file=stderr,
                    flush=True,
                )
                return False
            case _:
                time.sleep(INPUT_QUEUE_POLL_SEC)
    print(
        f"{TRANSPORT_TAG} ERROR timeout waiting for input delivered ({label}) "
        f"client_message_id={client_message_id} last_status={status!r}",
        file=stderr,
        flush=True,
    )
    return False


def is_implicit_sign_on_greeting(meta: dict[str, Any]) -> bool:
    source = str(meta.get("source") or "").strip()
    if source == "greeting":
        return True
    if meta.get("isOpening") is True:
        return True
    return False


def wait_implicit_sign_on_greeting(
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
        time.sleep(RECV_POLL_SEC)
    return None, {}, (408, "timeout waiting for implicit sign-on greeting")


def query_latest_memdoc_version(
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
    scope_chat = agent_scope_chat_id(user_id, agent_id)
    raw = psql(
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


def query_bootstrap_complete(
    repo_root: Path,
    config_path: Path,
    *,
    user_id: str,
    agent_id: str,
) -> bool:
    """Return whether interactive bootstrap is marked complete in context.json."""
    assert user_id != ""
    assert agent_id != ""
    scope_chat = agent_scope_chat_id(user_id, agent_id)
    raw = psql(
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
    return raw == "true"


def wait_bootstrap_complete_flag(
    repo_root: Path,
    config_path: Path,
    *,
    user_id: str,
    agent_id: str,
    timeout_sec: float,
    stderr: TextIO,
    skip_db_checks: bool,
) -> bool:
    assert user_id != ""
    assert agent_id != ""
    if skip_db_checks:
        return True
    deadline = time.monotonic() + timeout_sec
    last_raw = ""
    while time.monotonic() < deadline:
        scope_chat = agent_scope_chat_id(user_id, agent_id)
        last_raw = psql(
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
            return True
        time.sleep(EXPERIENCE_PROFILE_POLL_SEC)
    print(
        f"{TRANSPORT_TAG} ERROR timeout waiting for bootstrap_complete "
        f"(last={last_raw!r})",
        file=stderr,
        flush=True,
    )
    return False


def send_and_drain(
    bridge: Any,
    repo_root: Path,
    config_path: Path,
    *,
    agent_id: str,
    user_id: str,
    text: str,
    label: str,
    stderr: TextIO,
    skip_db_checks: bool,
    user_time_context: UserTimeContext | None = None,
    turn_timeout_sec: float = TURN_REPLY_TIMEOUT_SEC,
) -> TurnDrainResult:
    """Send one turn, wait for matching downlink, drain trailing frames, verify queue idle."""
    user_msg_uuid = send_turn(
        bridge,
        agent_id,
        text,
        user_time_context=user_time_context,
    )
    assistant_text, meta, err = wait_downlink_for_user_msg_uuid(
        bridge,
        expected_user_msg_uuid=user_msg_uuid,
        timeout_sec=turn_timeout_sec,
        label=label,
    )
    if err is not None:
        return TurnDrainResult(
            user_msg_uuid=user_msg_uuid,
            assistant_text=None,
            meta={},
            input_queue_status="",
            memdoc_user_seq=None,
            error=err,
        )
    drain_until_quiet(
        bridge,
        quiet_sec=TURN_TRAILING_QUIET_SEC,
        max_sec=turn_timeout_sec,
    )
    wait_input_queue_idle(
        repo_root,
        config_path,
        agent_id=agent_id,
        timeout_sec=turn_timeout_sec,
        label=label,
        stderr=stderr,
        skip_db_checks=skip_db_checks,
    )
    wait_output_queue_idle(
        repo_root,
        config_path,
        agent_id=agent_id,
        timeout_sec=turn_timeout_sec,
        label=label,
        stderr=stderr,
        skip_db_checks=skip_db_checks,
    )
    input_status = ""
    if not skip_db_checks:
        input_status = query_input_status_for_client_message_id(
            repo_root,
            config_path,
            agent_id=agent_id,
            client_message_id=user_msg_uuid,
        )
    user_doc = query_latest_memdoc_version(
        repo_root,
        config_path,
        user_id=user_id,
        agent_id=agent_id,
        document_kind="USER.md",
    )
    memdoc_user_seq = user_doc.sequence_id if user_doc is not None else None
    return TurnDrainResult(
        user_msg_uuid=user_msg_uuid,
        assistant_text=assistant_text,
        meta=meta,
        input_queue_status=input_status,
        memdoc_user_seq=memdoc_user_seq,
        error=None,
    )
