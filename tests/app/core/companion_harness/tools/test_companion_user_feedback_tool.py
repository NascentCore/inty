"""Tests for companion_record_user_feedback tool."""

from __future__ import annotations

import json
import uuid

import pytest

from app.core.companion_harness.companion.llm_runtime_events import (
    LlmRuntimeEventBind,
    companion_llm_runtime_event_bind_ctx,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.tools.companion_tool_runtime import execute_tool_call
from app.core.companion_harness.tools.companion_user_feedback import (
    COMPANION_RECORD_USER_FEEDBACK_TOOL_NAME,
    GITHUB_ISSUE_LABELS,
    GITHUB_ISSUE_TITLE_PREFIX,
    USER_FEEDBACK_JSONL_REL,
    ComplaintCategory,
    HarnessSnapshot,
    UserFeedbackInput,
    UserTurnCorrelation,
    build_github_issue_body,
    build_github_issue_title,
    build_harness_snapshot,
)


def _sample_snapshot() -> HarnessSnapshot:
    return HarnessSnapshot(
        feedback_id="fb-test-001",
        ts="2026-06-13T12:00:00+00:00",
        user_id="u-test",
        companion_id="c-test",
        chat_id="chat-test",
        memory_store_scope="u-test/c-test/chat-test",
        complaint_summary="Inty forgot my timezone again.",
        complaint_category=ComplaintCategory.MEMORY.value,
        correlation=UserTurnCorrelation(
            inty_trace_id="inty-trace-1",
            user_msg_uuid="user-msg-1",
            langsmith_trace_id="ls-trace-1",
            langsmith_trace_url="https://smith.langchain.com/o/x/projects/p/y/r/ls-trace-1",
            llm_phase="tool_background",
        ),
        context_mode="intimate",
        context_json='{"context_mode":"intimate"}\n',
        transcript_tail='{"role":"user","content":"why wrong timezone?"}\n',
        memory_docs={"USER.md": "# USER\nTZ: US/Pacific"},
        runtime_events=[],
        vcs_revision="abc123",
    )


@pytest.mark.asyncio
async def test_record_user_feedback_appends_snapshot_jsonl(tmp_path) -> None:
    rid = uuid.uuid4().hex[:12]
    scope = CompanionScope(f"u-ufb-{rid}", f"c-ufb-{rid}", f"chat-ufb-{rid}")
    store = MemoryStore(scope=scope, repository=None)
    store.write_document("context.json", '{"context_mode":"intimate"}\n')
    store.write_document("transcript.jsonl", '{"role":"user"}\n')
    store.write_document("USER.md", "# USER\n")

    bind = LlmRuntimeEventBind(
        memory_store=store,
        trace_id="trace-abc",
        user_msg_uuid="msg-uuid-abc",
        phase="tool_background",
        scene=None,
    )
    token = companion_llm_runtime_event_bind_ctx.set(bind)
    try:
        out = await execute_tool_call(
            store,
            COMPANION_RECORD_USER_FEEDBACK_TOOL_NAME,
            json.dumps(
                {
                    "complaint_summary": "You keep getting my timezone wrong.",
                    "complaint_category": "memory",
                },
                ensure_ascii=False,
            ),
        )
    finally:
        companion_llm_runtime_event_bind_ctx.reset(token)

    assert out.startswith("OK feedback_id=")
    assert "github_issue=skipped_no_token" in out
    body = store.read_document(USER_FEEDBACK_JSONL_REL)
    lines = [ln for ln in body.strip().split("\n") if ln.strip()]
    assert len(lines) >= 2
    snapshot_row = json.loads(lines[0])
    assert snapshot_row["kind"] == "snapshot"
    assert snapshot_row["complaint_summary"] == (
        "You keep getting my timezone wrong."
    )
    assert snapshot_row["complaint_category"] == "memory"
    assert snapshot_row["user_id"] == scope.user_id
    assert snapshot_row["correlation"]["user_msg_uuid"] == "msg-uuid-abc"
    assert snapshot_row["correlation"]["inty_trace_id"] == "trace-abc"
    skipped_row = json.loads(lines[1])
    assert skipped_row["kind"] == "github_issue_skipped"
    assert skipped_row["github_issue_status"] == "skipped_no_token"


@pytest.mark.asyncio
async def test_record_user_feedback_rejects_empty_summary(tmp_path) -> None:
    scope = CompanionScope("u", "c", "chat")
    store = MemoryStore(scope=scope, repository=None)
    out = await execute_tool_call(
        store,
        COMPANION_RECORD_USER_FEEDBACK_TOOL_NAME,
        json.dumps({"complaint_summary": "  ", "complaint_category": "tone"}),
    )
    assert out.startswith("ERROR:")


def test_build_harness_snapshot_reads_memory_docs(tmp_path) -> None:
    rid = uuid.uuid4().hex[:8]
    scope = CompanionScope(f"u-{rid}", f"c-{rid}", f"ch-{rid}")
    store = MemoryStore(scope=scope, repository=None)
    store.write_document("MEMORY.md", "# MEM\ntest memory")
    store.write_document("context.json", '{"context_mode":"public"}\n')

    snap = build_harness_snapshot(
        store,
        UserFeedbackInput(
            complaint_summary="bad tone",
            complaint_category=ComplaintCategory.TONE,
        ),
    )
    assert snap.context_mode == "public"
    assert "MEMORY.md" in snap.memory_docs
    assert snap.complaint_category == "tone"


def test_build_harness_snapshot_transcript_tail_is_recent_lines(tmp_path) -> None:
    scope = CompanionScope("u", "c", "chat")
    store = MemoryStore(scope=scope, repository=None)
    prefix = '{"role":"user","content":"EARLY_ONLY"}\n'
    filler = '{"role":"user","content":"f"}\n' * 800
    recent_marker = '{"role":"user","content":"RECENT_COMPLAINT"}\n'
    store.write_document("transcript.jsonl", prefix + filler + recent_marker)

    snap = build_harness_snapshot(
        store,
        UserFeedbackInput(
            complaint_summary="x",
            complaint_category=ComplaintCategory.OTHER,
        ),
    )
    assert "RECENT_COMPLAINT" in snap.transcript_tail
    assert "EARLY_ONLY" not in snap.transcript_tail


def test_github_issue_title_has_user_reported_prefix() -> None:
    title = build_github_issue_title(_sample_snapshot())
    assert title.startswith(GITHUB_ISSUE_TITLE_PREFIX)
    assert "memory:" in title


def test_github_issue_body_includes_langsmith_trace_id() -> None:
    body = build_github_issue_body(_sample_snapshot())
    assert "langsmith_trace_id" in body
    assert "`ls-trace-1`" in body
    assert "smith.langchain.com" in body
    assert "user_msg_uuid" in body
    assert "`user-msg-1`" in body
    assert "## Context (trace back to original session)" in body


def test_github_issue_labels_include_user_reported() -> None:
    assert "user-reported" in GITHUB_ISSUE_LABELS
    assert "agentic_companion" in GITHUB_ISSUE_LABELS
