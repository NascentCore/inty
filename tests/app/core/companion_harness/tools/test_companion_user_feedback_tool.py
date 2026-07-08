"""Tests for companion_record_user_feedback tool."""

from __future__ import annotations

import json
import os
import uuid

import pytest

from app.core.companion_harness.companion.llm_runtime_events import (
    LlmRuntimeEventBind,
    companion_llm_runtime_event_bind_ctx,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_path_constants import (
    CONTEXT_JSON_REL,
    TRANSCRIPT_JSONL_REL,
)
from app.core.companion_harness.tools.companion_tool_runtime import (
    execute_tool_call,
)
from app.core.companion_harness.tools.companion_user_feedback import (
    COMPANION_RECORD_USER_FEEDBACK_TOOL_NAME,
    USER_FEEDBACK_JSONL_REL,
    ComplaintCategory,
    HarnessSnapshot,
    UserFeedbackDisclosureMode,
    UserFeedbackInput,
    UserFeedbackToolOutcome,
    UserTurnCorrelation,
    build_harness_snapshot,
    extract_github_issue_url_from_tool_turn_messages,
    format_user_feedback_tool_result,
    parse_github_issue_url_from_feedback_tool_result,
    resolve_user_feedback_disclosure_mode,
    resolve_user_visible_feedback_display_text,
)
from app.core.companion_harness.tools.companion_user_feedback_github_issue import (
    GITHUB_ISSUE_TITLE_PREFIX,
    build_github_issue_labels,
    build_github_issue_body,
    build_github_issue_title,
    github_issue_severity_label_for_category,
)


from app.utils.github.issues import GithubIssueCreateResult


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
async def test_record_user_feedback_appends_snapshot_jsonl(
    tmp_path, monkeypatch
) -> None:
    from app.core.companion_harness.tools import companion_user_feedback as mod

    rid = uuid.uuid4().hex[:12]
    scope = CompanionScope(f"u-ufb-{rid}", f"c-ufb-{rid}", f"chat-ufb-{rid}")
    store = MemoryStore(scope=scope, repository=None)
    store.write_document(CONTEXT_JSON_REL, '{"context_mode":"intimate"}\n')
    store.write_document(TRANSCRIPT_JSONL_REL, '{"role":"user"}\n')
    store.write_document("USER.md", "# USER\n")

    bind = LlmRuntimeEventBind(
        memory_store=store,
        trace_id="trace-abc",
        user_msg_uuid="msg-uuid-abc",
        phase="tool_background",
        scene=None,
    )
    token = companion_llm_runtime_event_bind_ctx.set(bind)
    old_gh = os.environ.pop("GH_TOKEN", None)
    monkeypatch.setattr(
        mod,
        "resolve_user_feedback_disclosure_mode",
        lambda: UserFeedbackDisclosureMode.HIDDEN,
    )
    monkeypatch.setattr(
        mod, "load_user_feedback_github_config", lambda: ("o/r", "")
    )
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
        if old_gh is not None:
            os.environ["GH_TOKEN"] = old_gh

    assert out.startswith("OK feedback_id=")
    assert "feedback_recorded" in out
    assert "github_issue" not in out
    assert "http" not in out
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


def test_format_user_feedback_tool_result_hidden() -> None:
    out = format_user_feedback_tool_result(
        UserFeedbackToolOutcome(
            feedback_id="fb-1",
            disclosure=UserFeedbackDisclosureMode.HIDDEN,
            github_issue_url="https://github.com/o/r/issues/1",
            github_issue_number=1,
            github_skipped_reason=None,
        )
    )
    assert out == "OK feedback_id=fb-1 feedback_recorded"
    assert "github" not in out
    assert "http" not in out


def test_format_user_feedback_tool_result_visible() -> None:
    url = "https://github.com/NascentCore/inty/issues/42"
    out = format_user_feedback_tool_result(
        UserFeedbackToolOutcome(
            feedback_id="fb-2",
            disclosure=UserFeedbackDisclosureMode.VISIBLE,
            github_issue_url=url,
            github_issue_number=42,
            github_skipped_reason=None,
        )
    )
    assert "github_issue_url=" in out
    assert url in out
    assert "github_issue_number=42" in out


def test_parse_github_issue_url_from_feedback_tool_result() -> None:
    url = "https://github.com/NascentCore/inty/issues/7"
    out = f"OK feedback_id=fb-1 github_issue_url={url} github_issue_number=7"
    assert parse_github_issue_url_from_feedback_tool_result(out) == url
    assert (
        parse_github_issue_url_from_feedback_tool_result(
            "OK feedback_id=x feedback_recorded"
        )
        == ""
    )


def test_extract_github_issue_url_from_tool_turn_messages() -> None:
    url = "https://github.com/NascentCore/inty/issues/9"
    tool_out = (
        f"OK feedback_id=fb-1 github_issue_url={url} github_issue_number=9"
    )
    messages = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "tc-1",
                    "function": {
                        "name": COMPANION_RECORD_USER_FEEDBACK_TOOL_NAME
                    },
                }
            ],
        },
        {"role": "tool", "tool_call_id": "tc-1", "content": tool_out},
    ]
    assert extract_github_issue_url_from_tool_turn_messages(messages) == url


def test_build_user_feedback_disclosure_display_text_url_only() -> None:
    from app.core.companion_harness.tools.companion_user_feedback import (
        build_user_feedback_disclosure_display_text,
    )

    url = "https://github.com/NascentCore/inty/issues/11"
    assert (
        build_user_feedback_disclosure_display_text(
            issue_url=url,
            llm_reply="",
        )
        == url
    )


def test_build_user_feedback_disclosure_display_text_prepends_reply() -> None:
    from app.core.companion_harness.tools.companion_user_feedback import (
        build_user_feedback_disclosure_display_text,
    )

    url = "https://github.com/NascentCore/inty/issues/11"
    display = build_user_feedback_disclosure_display_text(
        issue_url=url,
        llm_reply="抱歉，我会更注意时区。",
    )
    assert display.startswith(url)
    assert "抱歉" in display


@pytest.mark.asyncio
async def test_append_user_feedback_issue_disclosure_to_output_queue_visible(
    monkeypatch,
) -> None:
    from unittest.mock import AsyncMock, patch

    from app.core.companion_harness.tools import companion_user_feedback as mod
    from app.core.companion_harness.agentic_companion.types import (
        OutputMessageKind,
    )

    class _FakeRecord:
        def __init__(self, message_id: str, text: str, sequence: int) -> None:
            self.message_id = message_id
            self.text = text
            self.sequence = sequence
            self.tool_background_started = False
            self.generated_images = ()
            self.trace_id = None
            self.langsmith_trace_id = None
            self.langsmith_run_id = None
            self.turn_recall = None

    issue_url = "https://github.com/NascentCore/inty/issues/3652"
    monkeypatch.setattr(
        mod,
        "resolve_user_feedback_disclosure_mode",
        lambda: UserFeedbackDisclosureMode.VISIBLE,
    )
    with patch(
        "app.core.companion_harness.agentic_companion.output_queue.AsyncSessionLocal"
    ) as session_cls:
        session = AsyncMock()
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        session_cls.return_value = session
        repo = AsyncMock()
        repo.append_agent_output = AsyncMock(
            return_value=_FakeRecord("msg-disclosure", issue_url, 3)
        )
        with patch(
            "app.core.companion_harness.agentic_companion.output_queue.PostgresOutputQueueRepository",
            return_value=repo,
        ):
            appended = (
                await mod.append_user_feedback_issue_disclosure_to_output_queue(
                    user_id="user-testing",
                    agent_id="agent-1",
                    batch_id="batch-1",
                    user_msg_uuid="client-msg-1",
                    issue_url=issue_url,
                    llm_reply="",
                )
            )

    assert appended is True
    persisted = repo.append_agent_output.await_args.args[0]
    assert persisted.batch_id == "batch-1"
    assert persisted.message_ids == ("client-msg-1",)
    assert persisted.kind == OutputMessageKind.TOOL_BACKGROUND
    assert persisted.text == issue_url


@pytest.mark.asyncio
async def test_append_user_feedback_issue_disclosure_skipped_when_hidden(
    monkeypatch,
) -> None:
    from unittest.mock import AsyncMock, patch

    from app.core.companion_harness.tools import companion_user_feedback as mod

    monkeypatch.setattr(
        mod,
        "resolve_user_feedback_disclosure_mode",
        lambda: UserFeedbackDisclosureMode.HIDDEN,
    )
    with patch(
        "app.core.companion_harness.agentic_companion.output_queue.AsyncSessionLocal"
    ) as session_cls:
        session = AsyncMock()
        session_cls.return_value = session
        appended = (
            await mod.append_user_feedback_issue_disclosure_to_output_queue(
                user_id="user-testing",
                agent_id="agent-1",
                batch_id="batch-1",
                user_msg_uuid="client-msg-1",
                issue_url="https://github.com/NascentCore/inty/issues/1",
                llm_reply="",
            )
        )
    assert appended is False
    session_cls.assert_not_called()


def test_resolve_user_visible_feedback_display_text_visible(
    monkeypatch,
) -> None:
    from app.core.companion_harness.tools import companion_user_feedback as mod

    url = "https://github.com/NascentCore/inty/issues/11"
    tool_out = (
        f"OK feedback_id=fb-1 github_issue_url={url} github_issue_number=11"
    )
    messages = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "tc-1",
                    "function": {
                        "name": COMPANION_RECORD_USER_FEEDBACK_TOOL_NAME
                    },
                }
            ],
        },
        {"role": "tool", "tool_call_id": "tc-1", "content": tool_out},
    ]
    monkeypatch.setattr(
        mod,
        "resolve_user_feedback_disclosure_mode",
        lambda: UserFeedbackDisclosureMode.VISIBLE,
    )
    resolved = resolve_user_visible_feedback_display_text(
        llm_reply="抱歉，我会更注意时区。",
        appended_turn_msgs=messages,
    )
    assert resolved is not None
    assert resolved.github_issue_url == url
    assert resolved.display_text.startswith(url)
    assert "抱歉" in resolved.display_text


def test_resolve_user_visible_feedback_display_text_hidden(monkeypatch) -> None:
    from app.core.companion_harness.tools import companion_user_feedback as mod

    monkeypatch.setattr(
        mod,
        "resolve_user_feedback_disclosure_mode",
        lambda: UserFeedbackDisclosureMode.HIDDEN,
    )
    assert (
        resolve_user_visible_feedback_display_text(
            llm_reply="ok",
            appended_turn_msgs=[],
        )
        is None
    )


def test_resolve_user_feedback_disclosure_mode(monkeypatch) -> None:
    from app.core import config as core_config

    class _App:
        def __init__(self, debug: bool) -> None:
            self.debug = debug

    class _Cfg:
        def __init__(self, debug: bool) -> None:
            self.app = _App(debug)

    monkeypatch.setattr(
        core_config,
        "global_config_loaded_from_config_yaml",
        _Cfg(True),
    )
    assert (
        resolve_user_feedback_disclosure_mode()
        == UserFeedbackDisclosureMode.VISIBLE
    )

    monkeypatch.setattr(
        core_config,
        "global_config_loaded_from_config_yaml",
        _Cfg(False),
    )
    assert (
        resolve_user_feedback_disclosure_mode()
        == UserFeedbackDisclosureMode.HIDDEN
    )


@pytest.mark.asyncio
async def test_record_user_feedback_hidden_starts_async_job(
    monkeypatch,
) -> None:
    from app.core.companion_harness.tools import companion_user_feedback as mod

    started: list[str] = []

    def _fake_start(*_args, **_kwargs) -> None:
        started.append("yes")

    monkeypatch.setattr(
        mod,
        "resolve_user_feedback_disclosure_mode",
        lambda: UserFeedbackDisclosureMode.HIDDEN,
    )
    monkeypatch.setattr(
        mod, "load_user_feedback_github_config", lambda: ("o/r", "tok")
    )
    monkeypatch.setattr(mod, "start_github_issue_job", _fake_start)

    rid = uuid.uuid4().hex[:8]
    scope = CompanionScope(f"u-{rid}", f"c-{rid}", f"ch-{rid}")
    store = MemoryStore(scope=scope, repository=None)
    store.write_document(CONTEXT_JSON_REL, '{"context_mode":"intimate"}\n')

    out = await execute_tool_call(
        store,
        COMPANION_RECORD_USER_FEEDBACK_TOOL_NAME,
        json.dumps(
            {
                "complaint_summary": "bad memory",
                "complaint_category": "memory",
            }
        ),
    )
    assert started == ["yes"]
    assert "feedback_recorded" in out
    assert "github_issue" not in out


@pytest.mark.asyncio
async def test_record_user_feedback_visible_sync_create(monkeypatch) -> None:
    from app.core.companion_harness.tools import companion_user_feedback as mod

    fake_url = "https://github.com/NascentCore/inty/issues/99"

    def _fake_file(*_args, **_kwargs) -> GithubIssueCreateResult:
        return GithubIssueCreateResult(url=fake_url, number=99)

    monkeypatch.setattr(
        mod,
        "resolve_user_feedback_disclosure_mode",
        lambda: UserFeedbackDisclosureMode.VISIBLE,
    )
    monkeypatch.setattr(
        mod, "load_user_feedback_github_config", lambda: ("o/r", "tok")
    )
    monkeypatch.setattr(mod, "file_github_issue_for_snapshot", _fake_file)

    scope = CompanionScope("u", "c", "chat")
    store = MemoryStore(scope=scope, repository=None)
    store.write_document(CONTEXT_JSON_REL, "{}\n")

    out = await execute_tool_call(
        store,
        COMPANION_RECORD_USER_FEEDBACK_TOOL_NAME,
        json.dumps(
            {
                "complaint_summary": "bad tone",
                "complaint_category": "tone",
            }
        ),
    )
    assert fake_url in out
    assert "github_issue_number=99" in out


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
    store.write_document(CONTEXT_JSON_REL, '{"context_mode":"public"}\n')

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


def test_build_harness_snapshot_transcript_tail_is_recent_lines(
    tmp_path,
) -> None:
    scope = CompanionScope("u", "c", "chat")
    store = MemoryStore(scope=scope, repository=None)
    prefix = '{"role":"user","content":"EARLY_ONLY"}\n'
    filler = '{"role":"user","content":"f"}\n' * 800
    recent_marker = '{"role":"user","content":"RECENT_COMPLAINT"}\n'
    store.write_document(TRANSCRIPT_JSONL_REL, prefix + filler + recent_marker)

    snap = build_harness_snapshot(
        store,
        UserFeedbackInput(
            complaint_summary="x",
            complaint_category=ComplaintCategory.OTHER,
        ),
    )
    assert "RECENT_COMPLAINT" in snap.transcript_tail
    assert "EARLY_ONLY" not in snap.transcript_tail


def test_github_issue_format() -> None:
    snap = _sample_snapshot()
    title = build_github_issue_title(snap)
    body = build_github_issue_body(snap)
    labels = build_github_issue_labels(snap)
    assert title.startswith(GITHUB_ISSUE_TITLE_PREFIX)
    assert "memory:" in title
    assert "user-reported" in labels
    assert "agentic_companion" in labels
    assert "bug" in labels
    assert "needs-triage" in labels
    assert "p2" in labels
    assert labels[-1] == github_issue_severity_label_for_category("memory")
    assert "`ls-trace-1`" in body
    assert "`user-msg-1`" in body
    assert "## Context (trace back to original session)" in body


def test_github_issue_severity_label_for_category() -> None:
    assert github_issue_severity_label_for_category("tool_failure") == "s1"
    assert github_issue_severity_label_for_category("tone") == "s3"
    assert github_issue_severity_label_for_category("memory") == "s2"
    assert github_issue_severity_label_for_category("unknown") == "s2"
