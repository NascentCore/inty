#!/usr/bin/env python3
"""Add GitHub issue refs to companion_harness TODOs that lack #NNNN anchors."""

from __future__ import annotations

import re
import sys
from pathlib import Path

TAG_TO_ISSUE: dict[str, int] = {
    "companion-package-reorg": 3409,
    "dreaming-day-rollup": 3376,
    "companion-multimodal-user-turn": 3293,
    "static-prompt-slice-memstore": 3506,
    "tool-bg-idle-starves-user-chat": 3123,
    "rename-memory-doc": 3400,
    "narrow-maintenance": 3375,
    "companion-session-eviction": 3444,
    "memdoc-path-constants": 3413,
    "companion-channel-tools": 3362,
    "ws-disconnect-lifecycle": 3256,
    "person-identity-schema": 3390,
    "crs-write-lattice": 3367,
    "companion-ws-bootstrap-downlink": 3209,
    "prompt-slice-dedup": 3417,
    "scope-listing-due-filter": 3423,
    "track-write-policy": 3367,
    "companion-dual-envelope-reasoning-channel": 3398,
    "cross-track-image-delivery": 3285,
    "memory-hierarchy-design": 3405,
    "ai-private-jsonl-write": 3375,
    "track-driven-system-messages-building": 3453,
    "telegram-meta-ops-tools": 3397,
    "code-structure": 3409,
    "bootstrap-prompt-single-source": 3463,
    "rename-channel-to-gateway": 3548,
    "consolidate-memory-doc-definitions": 3549,
    "offline-batch": 3547,
    "dreaming-cluster-lock": 3550,
    "dreaming-batch-langsmith-finally": 3551,
    "companion-user-feedback": 3552,
    "companion-langsmith-slice": 3553,
    "code-path-straightforwardness": 3516,
    "dreaming-transcript-invariant": 3376,
    "crs-turn-recall": 3343,
    "bootstrap-max-turns": 3463,
    "ai-private-splice-scheduled": 3375,
    "ai-private-persist-atomic": 3375,
    "user-feature": 3325,
    "abstraction": 3453,
    "structural-simplicity": 3516,
    "structual-simplicity": 3516,
    "code-consistency": 3413,
    "crs-persona-slice-registry": 3341,
    "experience-profile": 3343,
}

ROOTS = (
    Path("app/core/companion_harness"),
    Path("docs/imate/companion_harness"),
)

ISSUE_REF_RE = re.compile(r"(?:!|#)\d+")
TAG_RE = re.compile(r"TODO\(([^)]+)\)")


def _annotate_line(line: str) -> str:
    if "TODO" not in line or ISSUE_REF_RE.search(line):
        return line
    m = TAG_RE.search(line)
    if not m:
        return line
    tag = m.group(1).strip()
    issue = TAG_TO_ISSUE.get(tag)
    if issue is None:
        return line
    stripped = line.rstrip("\n")
    if stripped.endswith((".", "。", ")", "]", "`")):
        return f"{stripped} — #{issue}\n"
    return f"{stripped} — #{issue}\n"


def main() -> int:
    repo = Path(__file__).resolve().parents[3]
    changed_files = 0
    changed_lines = 0
    for root in ROOTS:
        base = repo / root
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.suffix not in {".py", ".md"}:
                continue
            text = path.read_text(encoding="utf-8")
            lines = text.splitlines(keepends=True)
            new_lines = [_annotate_line(line) for line in lines]
            if new_lines != lines:
                path.write_text("".join(new_lines), encoding="utf-8")
                delta = sum(1 for a, b in zip(lines, new_lines, strict=True) if a != b)
                changed_files += 1
                changed_lines += delta
                print(f"updated {path.relative_to(repo)} ({delta} lines)")
    print(f"done: {changed_files} files, {changed_lines} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
