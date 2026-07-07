"""Companion user complaint tool: harness snapshot + GitHub issue filing.

Design:
- Sync: capture ``HarnessSnapshot`` and append ``kind=snapshot`` to
  ``.companion_user_feedback.jsonl`` before returning to the LLM tool loop.
- GitHub filing: always attempted when token is configured (async when
  ``app.debug`` is false; sync when true so the tool result can carry the URL).
- Disclosure: ``app.debug`` controls GitHub URL/number in the LLM-visible tool
  result only — prod users see ``feedback_recorded`` without GitHub details.
  When ``app.debug`` is true, ``tool_background`` prepends the issue URL from
  the tool return to the user-visible tool-leg reply (deterministic; not LLM).
- Correlation: ``get_current_trace_info()`` + ``companion_llm_runtime_event_bind_ctx``
  at tool-call time (user-turn LangSmith trace + inty_trace_id / user_msg_uuid).
- GitHub REST lives in ``app.utils.github.issues``; issue title/body/labels in
  ``companion_user_feedback_github_issue`` (companion-domain, not generic utils).
- Token: agent.companion_harness.user_feedback_github.token, else GH_TOKEN.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

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
from app.core.companion_harness.memory.memory_store_path_constants import (
    COMPANION_USER_FEEDBACK_JSONL_REL,
    CONTEXT_JSON_REL,
    IDENTITY_MD_REL,
    MEMORY_MD_REL,
    SOUL_MD_REL,
    STYLE_MD_REL,
    TRANSCRIPT_JSONL_REL,
    USER_MD_REL,
)
from app.utils.github.issues import GithubIssueCreateResult
from app.utils.langsmith import get_current_trace_info

USER_FEEDBACK_JSONL_REL = COMPANION_USER_FEEDBACK_JSONL_REL
COMPANION_RECORD_USER_FEEDBACK_TOOL_NAME = "companion_record_user_feedback"

# Snapshot paths from canonical MemDoc path constants (#3413).
SNAPSHOT_DOC_PATHS: tuple[str, ...] = (
    CONTEXT_JSON_REL,
    IDENTITY_MD_REL,
    SOUL_MD_REL,
    STYLE_MD_REL,
    USER_MD_REL,
    MEMORY_MD_REL,
)
TRANSCRIPT_REL = TRANSCRIPT_JSONL_REL
TRANSCRIPT_TAIL_MAX_CHARS = 12_000
MEMORY_DOC_MAX_CHARS = 4_000

_FEEDBACK_KIND_SNAPSHOT = "snapshot"
_FEEDBACK_KIND_GITHUB_ISSUE_CREATED = "github_issue_created"
_FEEDBACK_KIND_GITHUB_ISSUE_SKIPPED = "github_issue_skipped"


class ComplaintCategory(StrEnum):
    BEHAVIOR = "behavior"
    MEMORY = "memory"
    TONE = "tone"
    TOOL_FAILURE = "tool_failure"
    OTHER = "other"


class UserFeedbackDisclosureMode(StrEnum):
    """Controls GitHub identifiers in the LLM-visible tool result only."""

    HIDDEN = "hidden"
    VISIBLE = "visible"


@dataclass(frozen=True)
class UserFeedbackToolOutcome:
    """Inputs to ``format_user_feedback_tool_result``."""

    feedback_id: str
    disclosure: UserFeedbackDisclosureMode
    github_issue_url: str
    github_issue_number: int
    github_skipped_reason: str | None


@dataclass(frozen=True)
class UserFeedbackVisibleDisplay:
    """Deterministic user-visible WS text when debug disclosure applies."""

    github_issue_url: str
    display_text: str


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


def truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n…[truncated]"


def tail_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return "…[truncated]\n" + text[-max_chars:]


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
    context_json = store.read_document_if_exists(CONTEXT_JSON_REL) or ""
    transcript_raw = store.read_document_if_exists(TRANSCRIPT_REL) or ""
    memory_docs: dict[str, str] = {}
    for rel in SNAPSHOT_DOC_PATHS:
        if rel == CONTEXT_JSON_REL:
            continue
        body = store.read_document_if_exists(rel)
        if body:
            memory_docs[rel] = truncate_text(body, MEMORY_DOC_MAX_CHARS)
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
        transcript_tail=tail_text(transcript_raw, TRANSCRIPT_TAIL_MAX_CHARS),
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


def append_user_feedback_record(
    store: MemoryStore, record: dict[str, Any]
) -> None:
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


def resolve_user_feedback_disclosure_mode() -> UserFeedbackDisclosureMode:
    """Return VISIBLE when ``app.debug`` is true so testers get issue URLs in tool output."""
    from app.core.config import global_config_loaded_from_config_yaml

    if global_config_loaded_from_config_yaml.app.debug:
        return UserFeedbackDisclosureMode.VISIBLE
    return UserFeedbackDisclosureMode.HIDDEN


def format_user_feedback_tool_result(outcome: UserFeedbackToolOutcome) -> str:
    """Build the LLM-visible tool result; HIDDEN never exposes GitHub identifiers."""
    base = f"OK feedback_id={outcome.feedback_id}"
    if outcome.disclosure == UserFeedbackDisclosureMode.HIDDEN:
        return f"{base} feedback_recorded"
    if outcome.github_issue_url.strip() and outcome.github_issue_number > 0:
        return (
            f"{base} github_issue_url={outcome.github_issue_url.strip()} "
            f"github_issue_number={outcome.github_issue_number}"
        )
    if outcome.github_skipped_reason:
        return f"{base} github_issue_status={outcome.github_skipped_reason}"
    return f"{base} feedback_recorded"


def parse_github_issue_url_from_feedback_tool_result(tool_result: str) -> str:
    """Parse ``github_issue_url=`` from a ``companion_record_user_feedback`` tool return."""
    for part in tool_result.split():
        if part.startswith("github_issue_url="):
            url = part.split("=", 1)[1].strip()
            if url.startswith("http"):
                return url
    return ""


def extract_github_issue_url_from_tool_turn_messages(
    appended_messages: list[dict[str, Any]],
) -> str:
    """Return issue URL from the latest successful ``companion_record_user_feedback`` tool row."""
    pending: dict[str, str] = {}
    found = ""
    for message in appended_messages:
        role = message.get("role")
        if role == "assistant":
            pending.clear()
            for tool_call in message.get("tool_calls") or []:
                if not isinstance(tool_call, dict):
                    continue
                tool_call_id = tool_call.get("id")
                function = tool_call.get("function")
                if not isinstance(function, dict):
                    continue
                raw_name = function.get("name")
                if isinstance(tool_call_id, str) and isinstance(raw_name, str):
                    name = raw_name.strip()
                    if name:
                        pending[tool_call_id] = name
            continue
        if role != "tool":
            continue
        tool_call_id = message.get("tool_call_id")
        if not isinstance(tool_call_id, str):
            continue
        if (
            pending.get(tool_call_id)
            != COMPANION_RECORD_USER_FEEDBACK_TOOL_NAME
        ):
            continue
        content = message.get("content")
        if not isinstance(content, str) or content.strip().startswith("ERROR"):
            continue
        url = parse_github_issue_url_from_feedback_tool_result(content)
        if url:
            found = url
    return found


def build_user_feedback_disclosure_display_text(
    *,
    issue_url: str,
    llm_reply: str,
) -> str:
    """Build deterministic user-visible text that discloses a filed GitHub issue."""
    url = issue_url.strip()
    assert url != ""
    reply = llm_reply.strip()
    if url in reply:
        return reply
    if reply:
        return f"{url}\n\n{reply}"
    return url


async def append_user_feedback_issue_disclosure_to_output_queue(
    *,
    user_id: str,
    agent_id: str,
    batch_id: str,
    user_msg_uuid: str,
    issue_url: str,
    llm_reply: str,
) -> bool:
    """Persist correlated OutputQueue disclosure when feedback runs outside AgenticLoop.

    Returns True when a visible disclosure row was appended (``app.debug`` only).
    """
    assert user_id != ""
    assert agent_id != ""
    assert batch_id != ""
    assert user_msg_uuid != ""
    assert issue_url.strip() != ""
    if (
        resolve_user_feedback_disclosure_mode()
        != UserFeedbackDisclosureMode.VISIBLE
    ):
        return False
    from app.core.companion_harness.agent_channel.scope import AgentScope
    from app.core.companion_harness.agentic_companion.output_queue import (
        OutputQueueAppendInput,
        get_output_queue_for_scope,
    )
    from app.core.companion_harness.agentic_companion.types import (
        OutputMessageKind,
    )

    display_text = build_user_feedback_disclosure_display_text(
        issue_url=issue_url,
        llm_reply=llm_reply,
    )
    scope = AgentScope(user_id=user_id, agent_id=agent_id)
    await get_output_queue_for_scope(scope).append_visible_message(
        OutputQueueAppendInput(
            kind=OutputMessageKind.TOOL_BACKGROUND,
            batch_id=batch_id,
            text=display_text,
            message_ids=(user_msg_uuid,),
            trace_id=None,
            langsmith_trace_id=None,
            langsmith_run_id=None,
            turn_recall=None,
        )
    )
    logger.info(
        "companion_user_feedback disclosure_output_queue batch_id={} "
        "user_msg_uuid={} url={}",
        batch_id,
        user_msg_uuid,
        issue_url.strip(),
    )
    return True


def resolve_user_visible_feedback_display_text(
    *,
    llm_reply: str,
    appended_turn_msgs: list[dict[str, Any]],
) -> UserFeedbackVisibleDisplay | None:
    """Prepend deterministic issue URL to tool-leg NL when ``app.debug`` disclosure is visible."""
    if (
        resolve_user_feedback_disclosure_mode()
        != UserFeedbackDisclosureMode.VISIBLE
    ):
        return None
    issue_url = extract_github_issue_url_from_tool_turn_messages(
        appended_turn_msgs
    )
    if not issue_url:
        return None
    display_text = build_user_feedback_disclosure_display_text(
        issue_url=issue_url,
        llm_reply=llm_reply,
    )
    return UserFeedbackVisibleDisplay(
        github_issue_url=issue_url,
        display_text=display_text,
    )


def file_github_issue_for_snapshot(
    snapshot: HarnessSnapshot,
    store: MemoryStore,
    *,
    github_repo: str,
    github_token: str,
) -> GithubIssueCreateResult:
    """POST GitHub issue synchronously and append ``github_issue_created`` JSONL."""
    from app.core.companion_harness.tools.companion_user_feedback_github_issue import (
        create_companion_user_feedback_github_issue,
    )

    try:
        result = create_companion_user_feedback_github_issue(
            snapshot,
            github_repo=github_repo,
            github_token=github_token,
        )
        append_github_issue_completion(
            store,
            feedback_id=snapshot.feedback_id,
            github_issue_url=result.url,
            github_issue_number=result.number,
        )
        logger.info(
            "companion_user_feedback github_issue_created feedback_id={} url={}",
            snapshot.feedback_id,
            result.url,
        )
        return result
    except Exception as exc:
        reason = f"github_error:{type(exc).__name__}:{exc}"
        append_github_issue_skipped(
            store,
            feedback_id=snapshot.feedback_id,
            reason=reason,
        )
        logger.warning(
            "companion_user_feedback github_issue_failed feedback_id={} err={}",
            snapshot.feedback_id,
            exc,
        )
        raise RuntimeError(reason) from exc


def _github_issue_worker(
    snapshot: HarnessSnapshot,
    store: MemoryStore,
    github_repo: str,
    github_token: str,
) -> None:
    # Concurrent tool_background threads share one MemoryStore; the lock serializes
    # read-modify-write appends so feedback lines are not lost.
    try:
        file_github_issue_for_snapshot(
            snapshot,
            store,
            github_repo=github_repo,
            github_token=github_token,
        )
    except RuntimeError:
        return


def start_github_issue_job(
    snapshot: HarnessSnapshot,
    store: MemoryStore,
    *,
    github_repo: str,
    github_token: str,
) -> None:
    worker = threading.Thread(
        target=_github_issue_worker,
        args=(snapshot, store, github_repo, github_token),
        name="inty-user-feedback-github",
        daemon=True,
    )
    worker.start()


def load_user_feedback_github_config() -> tuple[str, str]:
    from app.core.config import global_config_loaded_from_config_yaml

    harness_cfg = global_config_loaded_from_config_yaml.agent.companion_harness
    repo = harness_cfg.user_feedback_github.repo.strip()
    token = harness_cfg.user_feedback_github.token.strip()
    if not token:
        token = os.environ.get("GH_TOKEN", "").strip()
    return repo, token


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

    disclosure = resolve_user_feedback_disclosure_mode()
    github_repo, github_token = load_user_feedback_github_config()
    if not github_token.strip():
        append_github_issue_skipped(
            store,
            feedback_id=snapshot.feedback_id,
            reason="skipped_no_token",
        )
        return format_user_feedback_tool_result(
            UserFeedbackToolOutcome(
                feedback_id=snapshot.feedback_id,
                disclosure=disclosure,
                github_issue_url="",
                github_issue_number=0,
                github_skipped_reason="skipped_no_token",
            )
        )

    if disclosure == UserFeedbackDisclosureMode.VISIBLE:
        try:
            result = file_github_issue_for_snapshot(
                snapshot,
                store,
                github_repo=github_repo,
                github_token=github_token,
            )
        except RuntimeError as exc:
            return format_user_feedback_tool_result(
                UserFeedbackToolOutcome(
                    feedback_id=snapshot.feedback_id,
                    disclosure=disclosure,
                    github_issue_url="",
                    github_issue_number=0,
                    github_skipped_reason=str(exc),
                )
            )
        return format_user_feedback_tool_result(
            UserFeedbackToolOutcome(
                feedback_id=snapshot.feedback_id,
                disclosure=disclosure,
                github_issue_url=result.url,
                github_issue_number=result.number,
                github_skipped_reason=None,
            )
        )

    start_github_issue_job(
        snapshot,
        store,
        github_repo=github_repo,
        github_token=github_token,
    )
    return format_user_feedback_tool_result(
        UserFeedbackToolOutcome(
            feedback_id=snapshot.feedback_id,
            disclosure=disclosure,
            github_issue_url="",
            github_issue_number=0,
            github_skipped_reason=None,
        )
    )
