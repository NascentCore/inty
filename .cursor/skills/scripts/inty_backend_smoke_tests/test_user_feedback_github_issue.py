"""
Smoke: companion_record_user_feedback creates a real GitHub issue via GH_TOKEN.

Run from repo root:
  PYTHONPATH=. GH_TOKEN=... python3 \\
    .cursor/skills/scripts/inty_backend_smoke_tests/test_user_feedback_github_issue.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

_VERIFY_TAG = "[inty-server-module-verify]"


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in (here, *here.parents):
        if (p / "app").is_dir() and (p / "requirements.txt").is_file():
            return p
    raise RuntimeError("Cannot find Inty repo root")


def _emit(ok: bool, detail: str, code: int) -> None:
    line = f"{_VERIFY_TAG} RESULT: {'PASS' if ok else 'FAIL'} (exit={code}) {detail}"
    print(line, flush=True) if ok else print(line, file=sys.stderr, flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--close", action="store_true")
    args = parser.parse_args()

    if not (os.getenv("GH_TOKEN") or "").strip():
        _emit(False, "GH_TOKEN not set", 2)
        return 2

    root = _repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from app.core.companion_harness.companion.llm_runtime_events import (
        LlmRuntimeEventBind,
        companion_llm_runtime_event_bind_ctx,
    )
    from app.core.companion_harness.companion.scope import CompanionScope
    from app.core.companion_harness.memory.memory_store import MemoryStore
    from app.core.companion_harness.tools.companion_tool_runtime import execute_tool_call
    from app.core.companion_harness.memory.memory_store_path_constants import (
        COMPANION_USER_FEEDBACK_JSONL_REL,
    )
    from app.core.companion_harness.tools.companion_user_feedback import (
        COMPANION_RECORD_USER_FEEDBACK_TOOL_NAME,
    )
    from app.core.companion_harness.tools.companion_user_feedback_github_issue import (
        GITHUB_ISSUE_TITLE_PREFIX,
    )

    rid = uuid.uuid4().hex[:8]
    trace_id = f"smoke-inty-trace-{rid}"
    user_msg_uuid = f"smoke-user-msg-{rid}"
    scope = CompanionScope(f"u-smoke-{rid}", f"c-smoke-{rid}", f"chat-smoke-{rid}")
    store = MemoryStore(scope=scope, repository=None)
    store.write_document("context.json", '{"context_mode":"intimate"}\n')
    store.write_document("transcript.jsonl", '{"role":"user","content":"smoke"}\n')
    store.write_document("USER.md", "# USER\n")

    bind = LlmRuntimeEventBind(
        memory_store=store,
        trace_id=trace_id,
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
                        "complaint_summary": f"Smoke test user-feedback issue ({rid})",
                        "complaint_category": "other",
                    }
                ),
            )
        )
    finally:
        companion_llm_runtime_event_bind_ctx.reset(token)

    if not out.startswith("OK feedback_id="):
        _emit(False, f"unexpected tool output: {out}", 1)
        return 1
    if "github_issue_url=" not in out and "feedback_recorded" not in out:
        _emit(False, f"unexpected tool output: {out}", 1)
        return 1

    issue_url = ""
    issue_number = 0
    if "github_issue_url=" in out:
        for part in out.split():
            if part.startswith("github_issue_url="):
                issue_url = part.split("=", 1)[1]
            elif part.startswith("github_issue_number="):
                issue_number = int(part.split("=", 1)[1])

    deadline = time.monotonic() + 60.0
    while time.monotonic() < deadline and (not issue_url or issue_number <= 0):
        raw = store.read_document_if_exists(COMPANION_USER_FEEDBACK_JSONL_REL) or ""
        for line in raw.strip().split("\n"):
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("kind") == "github_issue_created":
                issue_url = str(row.get("github_issue_url") or "")
                issue_number = int(row.get("github_issue_number") or 0)
                break
        if issue_url:
            break
        time.sleep(1.0)

    if not issue_url or issue_number <= 0:
        _emit(False, "no github_issue_created JSONL within 60s", 1)
        return 1

    view = subprocess.run(
        ["gh", "issue", "view", str(issue_number), "--json", "title,labels,body"],
        capture_output=True,
        text=True,
        check=False,
    )
    if view.returncode != 0:
        _emit(False, view.stderr.strip(), 1)
        return 1

    data = json.loads(view.stdout)
    title = str(data.get("title") or "")
    labels = [lb.get("name") for lb in data.get("labels") or []]
    body = str(data.get("body") or "")
    if not title.startswith(GITHUB_ISSUE_TITLE_PREFIX):
        _emit(False, f"bad title: {title!r}", 1)
        return 1
    if trace_id not in body or user_msg_uuid not in body:
        _emit(False, "body missing correlation ids", 1)
        return 1
    if "agentic_companion" not in labels:
        _emit(False, f"missing agentic_companion: {labels}", 1)
        return 1
    if "user-reported" not in labels:
        _emit(False, f"missing user-reported: {labels}", 1)
        return 1
    if "bug" not in labels:
        _emit(False, f"missing bug: {labels}", 1)
        return 1

    if args.close:
        subprocess.run(
            [
                "gh",
                "issue",
                "close",
                str(issue_number),
                "--comment",
                "Closed by companion user-feedback smoke test.",
            ],
            check=False,
        )

    _emit(True, f"issue=#{issue_number} url={issue_url}", 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
