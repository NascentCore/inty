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
    "narrow-monolog": 3375,
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
    "memory-projection-pipeline": 3521,
    "memory-retrieval-selection": 3523,
    "slot-algebra-compaction": 3522,
    "memdoc-frontmatter": 3713,
    "conversation-projection": 3714,
    "memory-projection-dispersal": 3521,
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
    "prompt-plan-e2e": 3629,
    "langsmith-invocation-context": 3630,
    "tool-bg-async-client": 3631,
    "tool-bg-inline-agentic-loop": 3632,
    "langsmith-parent-run-orchestrator": 3633,
    "dreaming-agentic-loop": 3634,
    "structural-simplicity": 3516,
    "structual-simplicity": 3516,
    "code-consistency": 3413,
    "crs-persona-slice-registry": 3341,
    "experience-profile": 3343,
    "bootstrap-cohort-overlays": 3628,
    "track-compose-unify": 3398,
    "world-engine-agent-harness": 3702,
    "world-engine-agent-profile": 3701,
    "world-engine-agent-scope": 3704,
    "world-engine-firefly-kind": 3704,
    "world-engine-mailbox-spawn": 3703,
    "world-engine-firefly-test": 3705,
    "world-engine-summon-dismiss": 3706,
    "world-engine-firefly-clock": 3707,
    "world-engine-mailbox-prompt": 3708,
    "world-engine-l2-echo": 3709,
    "world-engine-experience-feedback": 3710,
    "world-engine-tracer-bullet": 3711,
    "world-engine-turn-spine": 3702,
}

ROOTS = (
    Path("app/core/companion_harness"),
    Path("docs/imate/companion_harness"),
)

ISSUE_REF_RE = re.compile(r"(?:!|#)\d+")
TAG_RE = re.compile(r"TODO\(([^)]+)\)")


def _todo_block_has_ref(lines: list[str], start_idx: int) -> bool:
    block = lines[start_idx]
    for j in range(start_idx + 1, min(start_idx + 5, len(lines))):
        nxt = lines[j]
        if nxt.strip().startswith(("def ", "class ", "@", "TODO(")):
            break
        block += "\n" + nxt
        if nxt.rstrip().endswith((".", "。", ")", "]", "`", "—", ";")):
            break
    return bool(ISSUE_REF_RE.search(block))


def _annotate_lines(lines: list[str]) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if "TODO" not in line or ISSUE_REF_RE.search(line) or _todo_block_has_ref(lines, i):
            out.append(line)
            i += 1
            continue
        m = TAG_RE.search(line)
        if not m:
            out.append(line)
            i += 1
            continue
        tag = m.group(1).strip()
        issue = TAG_TO_ISSUE.get(tag)
        if issue is None:
            out.append(line)
            i += 1
            continue
        stripped = line.rstrip("\n")
        keepends = line[len(stripped) :]
        out.append(f"{stripped} — #{issue}{keepends}")
        i += 1
    return out


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
            raw_lines = text.splitlines(keepends=True)
            plain = [line.rstrip("\n") for line in raw_lines]
            annotated = _annotate_lines(plain)
            new_lines = []
            for orig, new in zip(raw_lines, annotated, strict=True):
                keepends = orig[len(orig.rstrip("\n")) :]
                new_lines.append(new + keepends)
            if new_lines != raw_lines:
                path.write_text("".join(new_lines), encoding="utf-8")
                delta = sum(1 for a, b in zip(raw_lines, new_lines, strict=True) if a != b)
                changed_files += 1
                changed_lines += delta
                print(f"updated {path.relative_to(repo)} ({delta} lines)")
    print(f"done: {changed_files} files, {changed_lines} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
