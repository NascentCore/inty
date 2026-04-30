#!/usr/bin/env python3
"""Parse Inty-style chat export JSONL: show record shape and extract user/agent messages."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def role_and_content(record: dict[str, Any]) -> tuple[str | None, str | None]:
    mj = record.get("message_json")
    if not isinstance(mj, dict):
        return None, None
    mtype = mj.get("type")
    data = mj.get("data")
    if not isinstance(data, dict):
        return None, None
    content = data.get("content")
    if content is None:
        return None, None
    text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
    if mtype == "human":
        return "user", text
    if mtype == "ai":
        return "agent", text
    return str(mtype), text


def print_schema_sample(path: Path, n: int) -> None:
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= n:
                break
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            rid = obj.get("id")
            mj = obj.get("message_json")
            role, content = role_and_content(obj)
            preview = (content or "")[:120].replace("\n", " ")
            print(f"--- record {i + 1} id={rid} ---")
            print(f"  role (derived): {role}")
            print(f"  message_json.type: {mj.get('type') if isinstance(mj, dict) else mj}")
            if isinstance(mj, dict) and isinstance(mj.get("data"), dict):
                inner = mj["data"].get("type")
                print(f"  message_json.data.type (human rows): {inner!r}")
            print(f"  content preview: {preview!r}{'...' if content and len(content) > 120 else ''}")
            print()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "jsonl",
        nargs="?",
        default="/Users/yzhao/Downloads/chat_history_week1_0414_0417.jsonl",
        type=Path,
        help="Path to .jsonl chat export",
    )
    ap.add_argument("--sample", type=int, default=3, help="Print first N records structure (default 3)")
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Write all user/agent lines as text (default: <input>.dialogue.txt)",
    )
    ap.add_argument("--max-print", type=int, default=40, help="Max dialogue lines to print to stdout")
    args = ap.parse_args()

    path: Path = args.jsonl
    if not path.is_file():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 1

    out_path = args.output
    if out_path is None:
        out_path = path.with_name(path.name + ".dialogue.txt")

    print("Schema sample (first records):\n")
    print_schema_sample(path, args.sample)

    user_n = agent_n = skip_n = 0
    lines_out: list[str] = []

    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"warn: line {line_no} JSON error: {e}", file=sys.stderr)
                skip_n += 1
                continue
            role, text = role_and_content(obj)
            if role is None:
                skip_n += 1
                continue
            if role == "user":
                user_n += 1
            elif role == "agent":
                agent_n += 1
            lines_out.append(f"[{role}] {text}")

    total_messages = user_n + agent_n
    print(f"Summary: user={user_n}, agent={agent_n}, skipped_rows={skip_n}, total_turns={total_messages}")
    print(f"Writing full dialogue to: {out_path}\n")

    out_path.write_text("\n\n".join(lines_out) + "\n", encoding="utf-8")

    print(f"--- stdout preview (first {args.max_print} lines) ---\n")
    for i, s in enumerate(lines_out[: args.max_print]):
        preview = s[:500] + ("..." if len(s) > 500 else "")
        print(preview)
        print()
    if len(lines_out) > args.max_print:
        print(f"... ({len(lines_out) - args.max_print} more lines in file)\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
