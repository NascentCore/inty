"""Scan companion_harness TODO comments and validate GitHub issue references.

Generated entirely by Cursor Cloud Agent for epic consolidation hygiene.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

TODO_LINE_PATTERN = re.compile(
    r"(?P<prefix>.*?(?:TODO|FIXME)(?:\((?P<tag>[^)]*)\))?[:\s].*?)"
    r"(?:#(?P<issue>\d{4}))?",
    re.IGNORECASE,
)
BANG_ISSUE_PATTERN = re.compile(r"!(\d{4})")
ISSUE_REF_PATTERN = re.compile(r"#(\d{4})")

CLOSED_REDIRECTS: dict[int, int | None] = {
    3463: 3801,
    3369: None,
    3272: None,
    3413: None,
    3401: 3393,
    3400: 3817,
    3459: None,
}

TAG_REDIRECTS: dict[str, int] = {
    "crs-relationship-signal-log": 3773,
    "memdoc-belief-provenance": 3774,
    "counterfactual-fork-diff": 3775,
}


class TodoActionKind(StrEnum):
    """Hygiene action for one TODO comment line."""

    KEEP = "keep"
    RETARGET = "retarget"
    DELETE = "delete"


@dataclass(frozen=True)
class TodoAnchor:
    """One TODO/FIXME in companion_harness source; input to hygiene report."""

    path: str
    line: int
    raw_line: str
    issue_number: int | None
    tag: str | None


@dataclass(frozen=True)
class TodoHygieneRow:
    """One planned edit; output row in EPIC_CONSOLIDATION_AUDIT.md."""

    anchor: TodoAnchor
    action: TodoActionKind
    target_issue: int | None
    rationale: str


def scan_companion_harness_todos(root: str) -> list[TodoAnchor]:
    """Walk ``app/core/companion_harness/**/*.py`` and collect TODO anchors."""
    root_path = Path(root)
    anchors: list[TodoAnchor] = []
    for path in sorted(root_path.rglob("*.py")):
        rel = path.as_posix()
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if "TODO" not in line and "FIXME" not in line:
                continue
            tag_match = re.search(r"TODO(?:\(([^)]*)\))?", line, re.IGNORECASE)
            tag = tag_match.group(1) if tag_match else None
            issue_match = ISSUE_REF_PATTERN.search(line)
            issue_number = int(issue_match.group(1)) if issue_match else None
            if issue_number is None:
                bang_match = BANG_ISSUE_PATTERN.search(line)
                if bang_match:
                    issue_number = int(bang_match.group(1))
            anchors.append(
                TodoAnchor(
                    path=rel,
                    line=line_no,
                    raw_line=line,
                    issue_number=issue_number,
                    tag=tag,
                )
            )
    return anchors


def load_issue_state_cache(json_path: str) -> dict[int, str]:
    """Load issue audit JSON (# -> OPEN|CLOSED); no live gh in tests."""
    raw = json.loads(Path(json_path).read_text(encoding="utf-8"))
    state: dict[int, str] = {}
    for item in raw:
        number = int(item["number"])
        state[number] = str(item["state"]).upper()
    return state


def _redirect_for_closed(issue_number: int) -> tuple[TodoActionKind, int | None, str]:
    if issue_number not in CLOSED_REDIRECTS:
        return TodoActionKind.KEEP, issue_number, "open or unmapped closed issue"
    successor = CLOSED_REDIRECTS[issue_number]
    if successor is None:
        return TodoActionKind.DELETE, None, f"closed #{issue_number} shipped; remove TODO"
    return TodoActionKind.RETARGET, successor, f"closed #{issue_number} -> #{successor}"


def plan_todo_hygiene(
    anchors: list[TodoAnchor],
    issue_state: dict[int, str],
) -> list[TodoHygieneRow]:
    """Apply closed-ref redirect table and tag normalization rules."""
    rows: list[TodoHygieneRow] = []
    for anchor in anchors:
        issue_number = anchor.issue_number
        if anchor.tag in TAG_REDIRECTS and issue_number is None:
            target = TAG_REDIRECTS[anchor.tag]
            rows.append(
                TodoHygieneRow(
                    anchor=anchor,
                    action=TodoActionKind.RETARGET,
                    target_issue=target,
                    rationale=f"tag {anchor.tag} -> #{target}",
                )
            )
            continue
        if issue_number is None:
            rows.append(
                TodoHygieneRow(
                    anchor=anchor,
                    action=TodoActionKind.KEEP,
                    target_issue=None,
                    rationale="no issue reference",
                )
            )
            continue
        closed_state = issue_state.get(issue_number)
        if closed_state == "CLOSED":
            action, target, rationale = _redirect_for_closed(issue_number)
            rows.append(
                TodoHygieneRow(
                    anchor=anchor,
                    action=action,
                    target_issue=target,
                    rationale=rationale,
                )
            )
            continue
        rows.append(
            TodoHygieneRow(
                anchor=anchor,
                action=TodoActionKind.KEEP,
                target_issue=issue_number,
                rationale="open issue reference",
            )
        )
    return rows


def assert_no_closed_refs(
    anchors: list[TodoAnchor],
    issue_state: dict[int, str],
) -> None:
    """Raise AssertionError if any TODO still references a CLOSED issue."""
    violations: list[str] = []
    for anchor in anchors:
        if anchor.issue_number is None:
            continue
        if issue_state.get(anchor.issue_number) == "CLOSED":
            violations.append(f"{anchor.path}:{anchor.line} -> #{anchor.issue_number}")
    if violations:
        joined = "\n".join(violations)
        raise AssertionError(f"TODO lines reference closed issues:\n{joined}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit companion_harness TODO issue refs")
    parser.add_argument(
        "--root",
        default="app/core/companion_harness",
        help="Repo-root-relative companion_harness tree",
    )
    parser.add_argument(
        "--issue-cache",
        default=".inty/issue_audit_all.json",
        help="JSON from gh_issue_audit_json.sh",
    )
    args = parser.parse_args()
    anchors = scan_companion_harness_todos(args.root)
    issue_state = load_issue_state_cache(args.issue_cache)
    assert_no_closed_refs(anchors, issue_state)
    closed_planned = [
        row
        for row in plan_todo_hygiene(anchors, issue_state)
        if row.action != TodoActionKind.KEEP
    ]
    print(f"scanned {len(anchors)} TODO lines; {len(closed_planned)} planned hygiene rows")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
