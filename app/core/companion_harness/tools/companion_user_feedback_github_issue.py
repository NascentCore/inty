"""GitHub issue title/body for companion user-feedback snapshots."""

from __future__ import annotations

import json

from app.core.companion_harness.tools.companion_user_feedback import (
    HarnessSnapshot,
    UserTurnCorrelation,
    tail_text,
    truncate_text,
)
from app.utils.github.issues import (
    GithubIssueCreateInput,
    GithubIssueCreateResult,
    create_github_issue,
)

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


def companion_user_feedback_github_label_sets() -> tuple[tuple[str, ...], ...]:
    return (
        GITHUB_ISSUE_LABELS,
        tuple(lb for lb in GITHUB_ISSUE_LABELS if lb != "needs-triage"),
        tuple(
            lb
            for lb in GITHUB_ISSUE_LABELS
            if lb not in ("needs-triage", "user-reported")
        ),
        ("agentic_companion", "p2", "s2"),
    )


def _langsmith_url_cell(correlation: UserTurnCorrelation) -> str:
    url = correlation.langsmith_trace_url.strip()
    if url:
        return f"[{url}]({url})"
    return "`unavailable`"


def build_github_issue_title(snapshot: HarnessSnapshot) -> str:
    summary = snapshot.complaint_summary.replace("\n", " ").strip()
    title_tail = summary[:72]
    title = (
        f"{GITHUB_ISSUE_TITLE_PREFIX} {snapshot.complaint_category}: {title_tail}"
    )
    return title[:256]


def build_github_issue_body(snapshot: HarnessSnapshot) -> str:
    corr = snapshot.correlation
    ls_id = corr.langsmith_trace_id.strip() or "unavailable"
    context_excerpt = truncate_text(
        snapshot.context_json,
        GITHUB_BODY_MEMORY_DOC_MAX_CHARS,
    )
    transcript_excerpt = tail_text(
        snapshot.transcript_tail,
        GITHUB_BODY_TRANSCRIPT_MAX_CHARS,
    )
    memory_lines: list[str] = []
    for rel, body in sorted(snapshot.memory_docs.items()):
        excerpt = truncate_text(body, GITHUB_BODY_MEMORY_DOC_MAX_CHARS)
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


def create_companion_user_feedback_github_issue(
    snapshot: HarnessSnapshot,
    *,
    github_repo: str,
    github_token: str,
) -> GithubIssueCreateResult:
    repo = github_repo.strip()
    token = github_token.strip()
    assert repo
    assert token
    return create_github_issue(
        GithubIssueCreateInput(
            repo=repo,
            token=token,
            title=build_github_issue_title(snapshot),
            body=build_github_issue_body(snapshot),
            label_sets=companion_user_feedback_github_label_sets(),
        )
    )
