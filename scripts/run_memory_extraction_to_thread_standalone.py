#!/usr/bin/env python3
"""
单独执行记忆抽取中 to_thread 内的逻辑（_compute_users_to_extract_sync），
用于验证是否由该逻辑导致内存持续增加。不启动 push_worker。

用法（在仓库根目录，建议使用项目 venv）:
  export PYTHONPATH=.
  .venv/bin/python scripts/run_memory_extraction_to_thread_standalone.py
  .venv/bin/python scripts/run_memory_extraction_to_thread_standalone.py --log-file .cursor/standalone_to_thread.log --interval 5
  .venv/bin/python scripts/run_memory_extraction_to_thread_standalone.py --dry-run   # 仅加载输入并打日志后退出，不执行 sync

日志：默认写入 .cursor/standalone_to_thread.log，包含各阶段 RSS、sync 入口/返回、以及运行期间周期性内存采样。

CREATED_BY_AGENT
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path

# 先设置 cwd 为仓库根，再导入依赖 config 的模块（config 从 config.yaml 加载，默认当前目录）
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) != os.getcwd():
    os.chdir(_REPO_ROOT)

import psycopg

from app.core.config import global_config_loaded_from_config_yaml
from app.services.memory_extraction_service import (
    MEMORY_TYPE_USER_COMMON,
    _compute_users_to_extract_sync,
)
from app.services.chat_service import generate_session_id


def _rss_mb() -> float:
    try:
        import resource
        # Linux: ru_maxrss 单位为 KB
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    except Exception:
        return 0.0


def _load_user_to_chats_and_last(db_url: str):
    conn = psycopg.connect(db_url, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, id FROM chats WHERE is_active = true")
            rows = cur.fetchall()
        user_to_chats: dict = {}
        for uid, cid in rows:
            user_to_chats.setdefault(uid, []).append(cid)

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id, MAX(extracted_at) AS last_at
                FROM memory_extraction_log
                WHERE memory_type = %s
                GROUP BY user_id
                """,
                (MEMORY_TYPE_USER_COMMON,),
            )
            rows_last = cur.fetchall()
        user_to_last = {r[0]: r[1] for r in rows_last}
        return user_to_chats, user_to_last
    finally:
        conn.close()


def _write_log(log_path: Path, message: str, data: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(
        {"ts": time.time(), "message": message, "data": data},
        ensure_ascii=False,
    ) + "\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="单独执行记忆抽取 to_thread 逻辑并打内存/进度日志",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=_REPO_ROOT / ".cursor" / "standalone_to_thread.log",
        help="日志输出路径（NDJSON）",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=10.0,
        help="运行期间内存采样间隔（秒）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅加载输入并打日志后退出，不执行 sync",
    )
    args = parser.parse_args()
    log_path = args.log_file
    interval = args.interval

    cfg = getattr(global_config_loaded_from_config_yaml, "memory_extraction", None)
    if not cfg:
        print("未配置 memory_extraction，退出", file=sys.stderr)
        return 1
    thresh_new = cfg.trigger_new_user_messages
    thresh_incr = cfg.trigger_incremental_messages
    db_url = global_config_loaded_from_config_yaml.database.url

    _write_log(
        log_path,
        "standalone_start",
        {"rss_mb": _rss_mb(), "thresh_new": thresh_new, "thresh_incr": thresh_incr},
    )

    user_to_chats, user_to_last = _load_user_to_chats_and_last(db_url)
    total_chats = sum(len(v) for v in user_to_chats.values())
    distinct_lasts_count = len(set(user_to_last.values()))
    _write_log(
        log_path,
        "after_load_inputs",
        {
            "rss_mb": _rss_mb(),
            "users_with_chats": len(user_to_chats),
            "users_with_last": len(user_to_last),
            "total_chats": total_chats,
            "distinct_lasts_count": distinct_lasts_count,
        },
    )
    if args.dry_run:
        print(
            f"dry-run: 已加载 users_with_chats={len(user_to_chats)}, total_chats={total_chats}, distinct_lasts_count={distinct_lasts_count}, RSS≈{_rss_mb():.1f} MB"
        )
        return 0

    result_holder: list = []
    sync_done = threading.Event()

    def run_sync() -> None:
        try:
            res = _compute_users_to_extract_sync(
                user_to_chats, user_to_last, thresh_new, thresh_incr
            )
            result_holder.append(res)
        finally:
            sync_done.set()

    t0 = time.time()
    thread = threading.Thread(target=run_sync, daemon=False)
    thread.start()

    while not sync_done.wait(timeout=interval):
        _write_log(
            log_path,
            "sync_running_sample",
            {"rss_mb": _rss_mb(), "elapsed_sec": round(time.time() - t0, 1)},
        )

    thread.join()
    elapsed = time.time() - t0
    result = result_holder[0] if result_holder else []
    _write_log(
        log_path,
        "standalone_finished",
        {
            "rss_mb": _rss_mb(),
            "elapsed_sec": round(elapsed, 1),
            "result_count": len(result),
        },
    )
    print(f"to_thread 逻辑已返回: 待抽取用户数={len(result)}, 耗时={elapsed:.1f}s, 结束 RSS≈{_rss_mb():.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
