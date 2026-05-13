#!/usr/bin/env python3
"""
对节日记忆 JSON（run_festival_memory_extraction_to_json 或 --query 输出）按 (user_name, agent_name) 排序 memories 并写回。

用法: python tools/scripts/sort_festival_memory_json.py tmp/out.json
      python tools/scripts/sort_festival_memory_json.py --input tmp/out.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import cyclopts


def _sort_key(item: dict) -> tuple[str, str]:
    return (
        item.get("user_name") or item.get("user_id") or "",
        item.get("agent_name") or item.get("agent_id") or "",
    )


def main(
    input_path: Annotated[
        str,
        cyclopts.Parameter(name="--input", help="节日记忆 JSON 文件路径"),
    ] = "tmp/out.json",
) -> None:
    path = Path(input_path)
    if not path.exists():
        print(f"错误: 文件不存在 {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    memories = payload.get("memories")
    if not isinstance(memories, list):
        print("错误: JSON 中缺少或非列表的 memories 字段", file=sys.stderr)
        sys.exit(1)
    payload["memories"] = sorted(memories, key=_sort_key)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Sorted {len(memories)} memory(ies) by (user_name, agent_name) in {path}")


if __name__ == "__main__":
    app = cyclopts.App(
        help="按 (user_name, agent_name) 排序节日记忆 JSON 的 memories。"
    )
    app.default(main)
    app()
