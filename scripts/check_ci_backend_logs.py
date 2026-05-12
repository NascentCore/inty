#!/usr/bin/env python3
"""Fail CI when backend test logs contain unexpected runtime errors."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ERROR_PATTERNS = (
    re.compile(r"\|\s+ERROR\s+\|"),
    re.compile(r"\bTraceback \(most recent call last\):"),
    re.compile(r"\bUnhandled(?:Error|Exception)\b"),
)


def _matches_unexpected_error(line: str) -> bool:
    return any(pattern.search(line) for pattern in ERROR_PATTERNS)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan an Inty backend CI log for unexpected runtime errors."
    )
    parser.add_argument("log_path", type=Path)
    parser.add_argument(
        "--context-name",
        default="backend log",
        help="Human-readable name shown in CI output.",
    )
    args = parser.parse_args()

    if not args.log_path.is_file():
        print(
            f"{args.context_name}: log file not found: {args.log_path}",
            file=sys.stderr,
        )
        return 1

    hits: list[tuple[int, str]] = []
    for line_no, line in enumerate(
        args.log_path.read_text(errors="replace").splitlines(), 1
    ):
        if _matches_unexpected_error(line):
            hits.append((line_no, line))

    if not hits:
        print(f"{args.context_name}: no unexpected runtime errors found.")
        return 0

    print(
        f"{args.context_name}: found {len(hits)} unexpected runtime error log line(s):",
        file=sys.stderr,
    )
    for line_no, line in hits[:50]:
        print(f"{args.log_path}:{line_no}: {line}", file=sys.stderr)
    if len(hits) > 50:
        print(f"... {len(hits) - 50} more line(s) omitted", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
