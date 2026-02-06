#!/usr/bin/env python3
"""
解析 push_worker debug.log（NDJSON），按时间顺序输出 job_entry / job_exit / LOCATE 等事件，
便于与内存曲线对齐，验证「下一轮任务又开始了」「上一轮 to_thread 还没结束」等猜想。

用法:
  python scripts/parse_push_worker_debug_log.py [path/to/debug.log]
  默认读取 .cursor/debug.log（相对于仓库根目录）。

CREATED_BY_AGENT
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _parse_line(line: str) -> dict | None:
    line = line.strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def _relevant(rec: dict) -> bool:
    msg = rec.get("message") or ""
    loc = rec.get("location") or ""
    if "job_entry" in msg or "job_exit" in msg:
        return True
    if "LOCATE" in (rec.get("hypothesisId") or ""):
        return True
    if "memory_extraction_sync_entered" in msg or "get_users_to_extract_before_to_thread" in msg or "get_users_to_extract_after_to_thread" in msg:
        return True
    if "memory_extraction_before" in msg:
        return True
    return False


def _summary(rec: dict) -> str:
    ts = rec.get("timestamp")
    msg = rec.get("message") or ""
    data = rec.get("data") or {}
    job_id = data.get("job_id") or ""
    parts = [msg]
    if job_id:
        parts.append(f"job_id={job_id}")
    if "result_count" in data:
        parts.append(f"result_count={data['result_count']}")
    if "approx_queries_if_unbatched" in data:
        parts.append(f"approx_queries={data['approx_queries_if_unbatched']}")
    return " | ".join(parts)


def main() -> None:
    if len(sys.argv) >= 2:
        log_path = Path(sys.argv[1])
    else:
        log_path = _repo_root() / ".cursor" / "debug.log"

    if not log_path.exists():
        print(f"文件不存在: {log_path}", file=sys.stderr)
        sys.exit(1)

    records: list[tuple[int, dict]] = []
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            rec = _parse_line(line)
            if not rec or not _relevant(rec):
                continue
            ts = rec.get("timestamp")
            if ts is None:
                continue
            records.append((int(ts), rec))

    records.sort(key=lambda x: x[0])

    print("# 按时间排序的 job_entry / job_exit / LOCATE 事件（用于与内存曲线对齐）")
    print("# timestamp_ms | summary")
    print("# 若需本地时间，可将 timestamp_ms 视为毫秒时间戳换算。")
    print("-" * 80)
    for ts, rec in records:
        print(f"{ts} | {_summary(rec)}")


if __name__ == "__main__":
    main()
