"""
Smoke: companion user-feedback GitHub issue creation (real GitHub API).

Requires GH_TOKEN (PAT with issues:write on nascentcore/inty).

Run from repo root:
  PYTHONPATH=. python3 .cursor/skills/scripts/inty_backend_smoke_tests/test_user_feedback_github_issue.py

Optional:
  --repo nascentcore/inty
  --close   close issue after verify (default: leave open for manual triage)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import uuid
from pathlib import Path

_VERIFY_TAG = "[inty-server-module-verify]"


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in (here, *here.parents):
        if (p / "app").is_dir() and (p / "requirements.txt").is_file():
            return p
    raise RuntimeError("Cannot find Inty repo root")


def _emit(ok: bool, detail: str, exit_code: int) -> None:
    if ok:
        print(f"{_VERIFY_TAG} RESULT: PASS (exit={exit_code}) {detail}", flush=True)
    else:
        print(
            f"{_VERIFY_TAG} RESULT: FAIL (exit={exit_code}) {detail}",
            file=sys.stderr,
            flush=True,
        )


def _run() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="nascentcore/inty")
    parser.add_argument(
        "--close",
        action="store_true",
        help="Close created issue after verification",
    )
    args = parser.parse_args()

    token = (os.getenv("GH_TOKEN") or "").strip()
    if not token:
        _emit(False, "GH_TOKEN not set", 2)
        return 2

    root = _find_repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from app.core.companion_harness.companion.scope import CompanionScope
    from app.core.companion_harness.memory.memory_store import MemoryStore
    from app.core.companion_harness.tools.companion_user_feedback import (
        USER_FEEDBACK_JSONL_REL,
        ComplaintCategory,
        HarnessSnapshot,
        UserFeedbackInput,
        UserTurnCorrelation,
        build_harness_snapshot,
        tool_companion_record_user_feedback,
    )
    from app.core.companion_harness.tools.companion_user_feedback_github_issue import (
        GITHUB_ISSUE_TITLE_PREFIX,
        create_companion_user_feedback_github_issue,
    )

    rid = uuid.uuid4().hex[:8]
    scope = CompanionScope(f"u-smoke-{rid}", f"c-smoke-{rid}", f"chat-smoke-{rid}")
    store = MemoryStore(scope=scope, repository=None)
    store.write_document("context.json", '{"context_mode":"intimate"}\n')
    store.write_document(
        "transcript.jsonl",
        '{"role":"user","content":"smoke test complaint about timezone"}\n',
    )
    store.write_document("USER.md", "# USER\nTZ: US/Pacific\n")

    snapshot = build_harness_snapshot(
        store,
        UserFeedbackInput(
            complaint_summary=(
                f"Smoke test: cloud agent verify user-feedback GitHub issue ({rid})"
            ),
            complaint_category=ComplaintCategory.OTHER,
        ),
    )
    snapshot = HarnessSnapshot(
        feedback_id=snapshot.feedback_id,
        ts=snapshot.ts,
        user_id=snapshot.user_id,
        companion_id=snapshot.companion_id,
        chat_id=snapshot.chat_id,
        memory_store_scope=snapshot.memory_store_scope,
        complaint_summary=snapshot.complaint_summary,
        complaint_category=snapshot.complaint_category,
        correlation=UserTurnCorrelation(
            inty_trace_id=f"smoke-inty-trace-{rid}",
            user_msg_uuid=f"smoke-user-msg-{rid}",
            langsmith_trace_id=f"smoke-ls-trace-{rid}",
            langsmith_trace_url="https://smith.langchain.com/o/smoke/projects/p/smoke/r/smoke",
            llm_phase="tool_background",
        ),
        context_mode=snapshot.context_mode,
        context_json=snapshot.context_json,
        transcript_tail=snapshot.transcript_tail,
        memory_docs=snapshot.memory_docs,
        runtime_events=snapshot.runtime_events,
        vcs_revision=snapshot.vcs_revision,
    )

    result = create_companion_user_feedback_github_issue(
        snapshot,
        github_repo=args.repo,
        github_token=token,
    )
    issue_url = result.url
    issue_number = result.number
    if not issue_url or issue_number <= 0:
        _emit(False, "create_companion_user_feedback_github_issue returned empty", 1)
        return 1

    import subprocess

    view = subprocess.run(
        ["gh", "issue", "view", str(issue_number), "--json", "title,labels,body,url"],
        capture_output=True,
        text=True,
        check=False,
    )
    if view.returncode != 0:
        _emit(
            False,
            f"gh issue view failed: {view.stderr.strip()}",
            1,
        )
        return 1

    issue_data = json.loads(view.stdout)
    title = str(issue_data.get("title") or "")
    labels = [lb.get("name") for lb in issue_data.get("labels") or []]
    body = str(issue_data.get("body") or "")

    checks: list[str] = []
    if not title.startswith(GITHUB_ISSUE_TITLE_PREFIX):
        checks.append(f"title missing prefix: {title!r}")
    if "smoke-ls-trace-" + rid not in body:
        checks.append("body missing langsmith_trace_id")
    if f"smoke-user-msg-{rid}" not in body:
        checks.append("body missing user_msg_uuid")
    if "agentic_companion" not in labels:
        checks.append(f"missing agentic_companion label: {labels}")

    if checks:
        _emit(False, "; ".join(checks), 1)
        return 1

    # Full tool path: background thread + JSONL completion line
    store2_scope = CompanionScope(f"u-smoke2-{rid}", f"c-smoke2-{rid}", f"ch2-{rid}")
    store2 = MemoryStore(scope=store2_scope, repository=None)
    store2.write_document("context.json", '{"context_mode":"intimate"}\n')
    store2.write_document("transcript.jsonl", "")
    store2.write_document("USER.md", "# USER\n")

    import app.core.companion_harness.tools.companion_user_feedback as ufb

    original_loader = ufb.load_user_feedback_github_config

    def _smoke_config() -> tuple[str, str]:
        return (args.repo, token)

    ufb.load_user_feedback_github_config = _smoke_config
    try:
        out = __import__("asyncio").run(
            __import__(
                "app.core.companion_harness.tools.companion_tool_runtime",
                fromlist=["execute_tool_call"],
            ).execute_tool_call(
                store2,
                "companion_record_user_feedback",
                json.dumps(
                    {
                        "complaint_summary": f"Tool path smoke {rid}",
                        "complaint_category": "other",
                    }
                ),
            )
        )
    finally:
        ufb.load_user_feedback_github_config = original_loader

    if not out.startswith("OK feedback_id=") or "github_issue=queued" not in out:
        _emit(False, f"tool unexpected output: {out}", 1)
        return 1

    deadline = time.monotonic() + 60.0
    completion_url = ""
    while time.monotonic() < deadline:
        raw = store2.read_document_if_exists(USER_FEEDBACK_JSONL_REL) or ""
        for line in raw.strip().split("\n"):
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("kind") == "github_issue_created":
                completion_url = str(row.get("github_issue_url") or "")
                break
        if completion_url:
            break
        time.sleep(1.0)

    if not completion_url:
        _emit(False, "tool path: no github_issue_created JSONL within 60s", 1)
        return 1

    if args.close:
        subprocess.run(
            [
                "gh",
                "issue",
                "close",
                str(issue_number),
                "--comment",
                "Closed by cloud-agent smoke test (direct API path).",
            ],
            check=False,
        )

    _emit(
        True,
        f"direct_issue=#{issue_number} url={issue_url} tool_completion={completion_url}",
        0,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_run())
