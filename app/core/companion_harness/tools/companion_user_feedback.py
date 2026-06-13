"""Capture companion harness snapshot on user complaint and file GitHub issue in background.

Generated entirely by Cursor agent.
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import requests
from loguru import logger

from app.core.build_info import vcs_revision
from app.core.companion_harness.companion.llm_runtime_events import (
    companion_llm_runtime_event_bind_ctx,
)
from app.core.companion_harness.companion.runtime_events import (
    read_runtime_events,
)
from app.core.companion_harness.companion.utc import utc_iso_ts
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.utils.langsmith import get_current_trace_info

USER_FEEDBACK_JSONL_REL = ".companion_user_feedback.jsonl"
COMPANION_RECORD_USER_FEEDBACK_TOOL_NAME = "companion_record_user_feedback"

SNAPSHOT_DOC_PATHS: tuple[str, ...] = (
    "context.json",
    "IDENTITY.md",
    "SOUL.md",
    "STYLE.md",
    "USER.md",
    "MEMORY.md",
)
TRANSCRIPT_REL = "transcript.jsonl"
TRANSCRIPT_TAIL_MAX_CHARS = 12_000
MEMORY_DOC_MAX_CHARS = 4_000
GITHUB_BODY_TRANSCRIPT_MAX_CHARS = 2_000
GITHUB_BODY_MEMORY_DOC_MAX_CHARS = 500
GITHUB_ISSUE_TITLE_PREFIX = "[user-reported]"
GITHUB_ISSUE_LABELS: tuple[str, ...] = (
    "user-reported",
    "agentic_companion",
    "needs-triage",
    "p2",
    "s2",
)

_FEEDBACK_KIND_SNAPSHOT = "snapshot"
_FEEDBACK_KIND_GITHUB_ISSUE_CREATED = "github_issue_created"
_FEEDBACK_KIND_GITHUB_ISSUE_SKIPPED = "github_issue_skipped"


class ComplaintCategory(StrEnum):
    BEHAVIOR = "behavior"
    MEMORY = "memory"
    TONE = "tone"
    TOOL_FAILURE = "tool_failure"
    OTHER = "other"


@dataclass(frozen=True)
class UserFeedbackInput:
    complaint_summary: str
    complaint_category: ComplaintCategory


@dataclass(frozen=True)
class UserTurnCorrelation:
    inty_trace_id: str
    user_msg_uuid: str
    langsmith_trace_id: str
    langsmith_trace_url: str
    llm_phase: str


@dataclass(frozen=True)
class HarnessSnapshot:
    feedback_id: str
    ts: str
    user_id: str
    companion_id: str
    chat_id: str
    memory_store_scope: str
    complaint_summary: str
    complaint_category: str
    correlation: UserTurnCorrelation
    context_mode: str
    context_json: str
    transcript_tail: str
    memory_docs: dict[str, str]
    runtime_events: list[dict[str, Any]]
    vcs_revision: str


@dataclass(frozen=True)
class GithubIssueConfig:
    repo: str
    token: str


def _truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n…[truncated]"


def _parse_context_mode(context_json: str) -> str:
    raw = (context_json or "").strip()
    if not raw:
        return ""
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return ""
    if not isinstance(obj, dict):
        return ""
    mode = obj.get("context_mode")
    if mode is None:
        return ""
    return str(mode).strip()


def resolve_user_turn_correlation() -> UserTurnCorrelation:
    ls_trace_id, ls_trace_url = get_current_trace_info()
    bind = companion_llm_runtime_event_bind_ctx.get()
    if bind is None:
        return UserTurnCorrelation(
            inty_trace_id="",
            user_msg_uuid="",
            langsmith_trace_id=ls_trace_id or "",
            langsmith_trace_url=ls_trace_url or "",
            llm_phase="",
        )
    return UserTurnCorrelation(
        inty_trace_id=bind.trace_id,
        user_msg_uuid=bind.user_msg_uuid,
        langsmith_trace_id=ls_trace_id or "",
        langsmith_trace_url=ls_trace_url or "",
        llm_phase=bind.phase,
    )


def build_harness_snapshot(
    store: MemoryStore,
    feedback_input: UserFeedbackInput,
) -> HarnessSnapshot:
    feedback_id = str(uuid.uuid4())
    scope = store.scope
    context_json = store.read_document_if_exists("context.json") or ""
    transcript_raw = store.read_document_if_exists(TRANSCRIPT_REL) or ""
    memory_docs: dict[str, str] = {}
    for rel in SNAPSHOT_DOC_PATHS:
        if rel == "context.json":
            continue
        body = store.read_document_if_exists(rel)
        if body:
            memory_docs[rel] = _truncate_text(body, MEMORY_DOC_MAX_CHARS)
    return HarnessSnapshot(
        feedback_id=feedback_id,
        ts=utc_iso_ts(),
        user_id=scope.user_id,
        companion_id=scope.companion_id,
        chat_id=scope.chat_id,
        memory_store_scope=scope.registry_key(),
        complaint_summary=feedback_input.complaint_summary,
        complaint_category=feedback_input.complaint_category.value,
        correlation=resolve_user_turn_correlation(),
        context_mode=_parse_context_mode(context_json),
        context_json=context_json,
        transcript_tail=_truncate_text(transcript_raw, TRANSCRIPT_TAIL_MAX_CHARS),
        memory_docs=memory_docs,
        runtime_events=read_runtime_events(store, limit=5),
        vcs_revision=vcs_revision(),
    )


def _snapshot_to_record(snapshot: HarnessSnapshot) -> dict[str, Any]:
    corr = snapshot.correlation
    return {
        "kind": _FEEDBACK_KIND_SNAPSHOT,
        "feedback_id": snapshot.feedback_id,
        "ts": snapshot.ts,
        "user_id": snapshot.user_id,
        "companion_id": snapshot.companion_id,
        "chat_id": snapshot.chat_id,
        "memory_store_scope": snapshot.memory_store_scope,
        "complaint_summary": snapshot.complaint_summary,
        "complaint_category": snapshot.complaint_category,
        "correlation": {
            "inty_trace_id": corr.inty_trace_id,
            "user_msg_uuid": corr.user_msg_uuid,
            "langsmith_trace_id": corr.langsmith_trace_id,
            "langsmith_trace_url": corr.langsmith_trace_url,
            "llm_phase": corr.llm_phase,
        },
        "context_mode": snapshot.context_mode,
        "context_json": snapshot.context_json,
        "transcript_tail": snapshot.transcript_tail,
        "memory_docs": snapshot.memory_docs,
        "runtime_events": snapshot.runtime_events,
        "vcs_revision": snapshot.vcs_revision,
    }


def append_user_feedback_record(store: MemoryStore, record: dict[str, Any]) -> None:
    store.append_jsonl_record(USER_FEEDBACK_JSONL_REL, record)


def append_github_issue_completion(
    store: MemoryStore,
    *,
    feedback_id: str,
    github_issue_url: str,
    github_issue_number: int,
) -> None:
    append_user_feedback_record(
        store,
        {
            "kind": _FEEDBACK_KIND_GITHUB_ISSUE_CREATED,
            "feedback_id": feedback_id,
            "ts": utc_iso_ts(),
            "github_issue_url": github_issue_url,
            "github_issue_number": github_issue_number,
        },
    )


def append_github_issue_skipped(
    store: MemoryStore,
    *,
    feedback_id: str,
    reason: str,
) -> None:
    append_user_feedback_record(
        store,
        {
            "kind": _FEEDBACK_KIND_GITHUB_ISSUE_SKIPPED,
            "feedback_id": feedback_id,
            "ts": utc_iso_ts(),
            "github_issue_status": reason,
        },
    )


def _langsmith_url_cell(correlation: UserTurnCorrelation) -> str:
    url = correlation.langsmith_trace_url.strip()
    if url:
        return f"[{url}]({url})"
    return "`unavailable`"


def build_github_issue_title(snapshot: HarnessSnapshot) -> str:
    summary = snapshot.complaint_summary.replace("\n", " ").strip()
    title_tail = _truncate_text(summary, 72).replace("\n", " ")
    return (
        f"{GITHUB_ISSUE_TITLE_PREFIX} {snapshot.complaint_category}: {title_tail}"
    )


def build_github_issue_body(snapshot: HarnessSnapshot) -> str:
    corr = snapshot.correlation
    ls_id = corr.langsmith_trace_id.strip() or "unavailable"
    context_excerpt = _truncate_text(
        snapshot.context_json,
        GITHUB_BODY_MEMORY_DOC_MAX_CHARS,
    )
    transcript_excerpt = _truncate_text(
        snapshot.transcript_tail,
        GITHUB_BODY_TRANSCRIPT_MAX_CHARS,
    )
    memory_lines: list[str] = []
    for rel, body in sorted(snapshot.memory_docs.items()):
        excerpt = _truncate_text(body, GITHUB_BODY_MEMORY_DOC_MAX_CHARS)
        memory_lines.append(f"#### {rel}\n```\n{excerpt}\n```")
    memory_block = "\n\n".join(memory_lines) if memory_lines else "_none_"
    runtime_block = (
        json.dumps(snapshot.runtime_events, ensure_ascii=False, indent=2)
        if snapshot.runtime_events
        else "_none_"
    )
    return "\n".join(
        [
            "## Summary",
            "",
            snapshot.complaint_summary,
            "",
            "## Context (trace back to original session)",
            "",
            "| Field | Value |",
            "|-------|-------|",
            f"| feedback_id | `{snapshot.feedback_id}` |",
            f"| complaint_category | `{snapshot.complaint_category}` |",
            f"| user_id | `{snapshot.user_id}` |",
            f"| companion_id (agent_id) | `{snapshot.companion_id}` |",
            f"| chat_id | `{snapshot.chat_id}` |",
            f"| memory_store_scope | `{snapshot.memory_store_scope}` |",
            f"| user_msg_uuid | `{corr.user_msg_uuid}` |",
            f"| inty_trace_id | `{corr.inty_trace_id}` |",
            f"| langsmith_trace_id | `{ls_id}` |",
            f"| langsmith_trace_url | {_langsmith_url_cell(corr)} |",
            f"| llm_phase | `{corr.llm_phase}` |",
            f"| context_mode | `{snapshot.context_mode}` |",
            f"| reported_at_utc | `{snapshot.ts}` |",
            f"| vcs_revision | `{snapshot.vcs_revision}` |",
            "",
            "> Automated report from `companion_record_user_feedback` tool.",
            "> Full harness snapshot in MemoryStore "
            f"`.companion_user_feedback.jsonl` (feedback_id above).",
            "",
            "## Harness snapshot excerpt (GitHub body caps: transcript 2k, memory 500/doc)",
            "",
            "### context.json",
            "```",
            context_excerpt,
            "```",
            "",
            "### transcript tail",
            "```",
            transcript_excerpt,
            "```",
            "",
            "### memory docs (truncated)",
            memory_block,
            "",
            "### recent runtime events",
            "```json",
            runtime_block,
            "```",
            "",
            "## Acceptance criteria",
            "",
            "- [ ] Reproduce from langsmith_trace_url + user_msg_uuid",
            f"- [ ] Verify complaint_category={snapshot.complaint_category}",
            "- [ ] Fix or document expected behavior",
            "",
            "## Out of scope",
            "",
            "- User-facing apology copy (handled in companion chat)",
        ]
    )


def create_github_issue(
    snapshot: HarnessSnapshot,
    github_config: GithubIssueConfig,
) -> tuple[str, int]:
    repo = github_config.repo.strip()
    token = github_config.token.strip()
    assert repo
    assert token
    url = f"https://api.github.com/repos/{repo}/issues"
    payload = {
        "title": build_github_issue_title(snapshot),
        "body": build_github_issue_body(snapshot),
        "labels": list(GITHUB_ISSUE_LABELS),
    }
    resp = requests.post(
        url,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json=payload,
        timeout=30.0,
    )
    if resp.status_code == 422:
        payload["labels"] = [
            lb for lb in GITHUB_ISSUE_LABELS if lb != "needs-triage"
        ]
        resp = requests.post(
            url,
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json=payload,
            timeout=30.0,
        )
    resp.raise_for_status()
    data = resp.json()
    issue_url = str(data.get("html_url") or "").strip()
    issue_number = int(data.get("number") or 0)
    assert issue_url
    assert issue_number > 0
    return issue_url, issue_number


def _github_issue_worker(
    snapshot: HarnessSnapshot,
    store: MemoryStore,
    github_config: GithubIssueConfig,
) -> None:
    try:
        issue_url, issue_number = create_github_issue(snapshot, github_config)
        append_github_issue_completion(
            store,
            feedback_id=snapshot.feedback_id,
            github_issue_url=issue_url,
            github_issue_number=issue_number,
        )
        logger.info(
            "companion_user_feedback github_issue_created feedback_id={} url={}",
            snapshot.feedback_id,
            issue_url,
        )
    except Exception as exc:
        append_github_issue_skipped(
            store,
            feedback_id=snapshot.feedback_id,
            reason=f"github_error:{type(exc).__name__}:{exc}",
        )
        logger.warning(
            "companion_user_feedback github_issue_failed feedback_id={} err={}",
            snapshot.feedback_id,
            exc,
        )


def start_github_issue_job(
    snapshot: HarnessSnapshot,
    store: MemoryStore,
    github_config: GithubIssueConfig,
) -> None:
    worker = threading.Thread(
        target=_github_issue_worker,
        args=(snapshot, store, github_config),
        name="inty-user-feedback-github",
        daemon=True,
    )
    worker.start()


def load_user_feedback_github_config() -> GithubIssueConfig:
    from app.core.config import global_config_loaded_from_config_yaml

    harness_cfg = global_config_loaded_from_config_yaml.app.features.companion_harness
    return GithubIssueConfig(
        repo=harness_cfg.user_feedback_github_repo,
        token=harness_cfg.user_feedback_github_token,
    )


def tool_companion_record_user_feedback(
    store: MemoryStore,
    arguments: dict[str, Any],
) -> str:
    raw_summary = arguments.get("complaint_summary")
    raw_category = arguments.get("complaint_category")
    if not isinstance(raw_summary, str):
        return "ERROR: complaint_summary must be a string"
    if not isinstance(raw_category, str):
        return "ERROR: complaint_category must be a string"
    summary = raw_summary.strip()
    if not summary:
        return "ERROR: complaint_summary must be non-empty"
    try:
        category = ComplaintCategory(raw_category.strip())
    except ValueError:
        allowed = ", ".join(m.value for m in ComplaintCategory)
        return f"ERROR: complaint_category must be one of: {allowed}"

    feedback_input = UserFeedbackInput(
        complaint_summary=summary,
        complaint_category=category,
    )
    snapshot = build_harness_snapshot(store, feedback_input)
    append_user_feedback_record(store, _snapshot_to_record(snapshot))

    github_config = load_user_feedback_github_config()
    if not github_config.token.strip():
        append_github_issue_skipped(
            store,
            feedback_id=snapshot.feedback_id,
            reason="skipped_no_token",
        )
        return (
            f"OK feedback_id={snapshot.feedback_id} "
            "github_issue=skipped_no_token"
        )

    start_github_issue_job(snapshot, store, github_config)
    return f"OK feedback_id={snapshot.feedback_id} github_issue=queued"
