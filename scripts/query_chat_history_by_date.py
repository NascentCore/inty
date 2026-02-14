#!/usr/bin/env python3
"""
按日期与可选筛选条件查询 chat_history，输出匹配的 (user_id, agent_id) 对及可选的 user_name、agent_name 与消息列表。

默认从只读副本（config.database.replica_host/replica_port）读取；无副本配置时可用 --no-replica 改为主库。
复用 app.services.festival_memory_service 的 28 小时时间窗与轮数筛选逻辑及 get_messages_for_user_agent_sync。
运行前需保证 config.yaml 存在（可用 --config 复制）。

用法:
    export PYTHONPATH=.
    python scripts/query_chat_history_by_date.py --date 2025-12-25
    python scripts/query_chat_history_by_date.py --date 2025-12-25 --timezone America/Los_Angeles --output-json out.json --include-messages
    python scripts/query_chat_history_by_date.py --config devops/config.yaml.prod --date 2025-12-25 --min-rounds 10
    python scripts/query_chat_history_by_date.py --no-replica --date 2025-12-25
"""

from __future__ import annotations

import json
import logging
import shutil
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Any, Optional, Tuple

import cyclopts
import psycopg

logger = logging.getLogger(__name__)

# 在解析 CLI 后、导入 app 前设置 config.yaml
CONFIG_YAML = "config.yaml"


def _repo_root() -> Path:
    """仓库根目录（scripts 的上一级）。"""
    return Path(__file__).resolve().parent.parent


def _ensure_config(config_path: Optional[str]) -> None:
    """若提供 --config 则复制到 cwd 的 config.yaml；否则要求 cwd 下已存在 config.yaml。"""
    cwd = Path.cwd()
    target = cwd / CONFIG_YAML
    if config_path:
        src = Path(config_path)
        if not src.is_absolute():
            src = _repo_root() / config_path
        if not src.exists():
            print(f"错误: 配置文件不存在: {src}", file=sys.stderr)
            sys.exit(1)
        shutil.copy2(src, target)
        logger.debug("已复制配置到 %s", target)
    else:
        if not target.exists():
            print(
                f"错误: 未指定 --config 且当前目录下不存在 {CONFIG_YAML}，请在仓库根目录运行或使用 --config PATH",
                file=sys.stderr,
            )
            sys.exit(1)


def _fetch_user_and_agent_names(
    pairs: list[Tuple[str, str]],
    connection: Any,
    db_url: str,
) -> Tuple[dict[str, Optional[str]], dict[str, Optional[str]]]:
    """
    批量查询 user_id -> nickname、agent_id -> name。
    connection 不为 None 时复用该连接；否则用 db_url 建立临时连接并关闭。
    """
    user_ids = list({uid for uid, _ in pairs})
    agent_ids = list({aid for _, aid in pairs})
    user_id_to_name: dict[str, Optional[str]] = {uid: None for uid in user_ids}
    agent_id_to_name: dict[str, Optional[str]] = {aid: None for aid in agent_ids}

    def run_queries(conn: Any) -> None:
        with conn.cursor() as cur:
            if user_ids:
                ph = ",".join("%s" for _ in user_ids)
                cur.execute(
                    f"SELECT id, nickname FROM users WHERE id IN ({ph})",
                    user_ids,
                )
                for row in cur.fetchall():
                    user_id_to_name[row[0]] = row[1]
            if agent_ids:
                ph = ",".join("%s" for _ in agent_ids)
                cur.execute(
                    f"SELECT id, name FROM agents WHERE id IN ({ph})",
                    agent_ids,
                )
                for row in cur.fetchall():
                    agent_id_to_name[row[0]] = row[1]

    if connection is not None and not getattr(connection, "closed", True):
        run_queries(connection)
    else:
        conn = psycopg.connect(db_url, autocommit=True)
        try:
            run_queries(conn)
        finally:
            conn.close()

    return user_id_to_name, agent_id_to_name


def main(
    date_arg: Annotated[
        str,
        cyclopts.Parameter(name="--date", help="日期 YYYY-MM-DD，用于 28 小时时间窗（该时区当日 00:00 至次日 04:00）。"),
    ],
    timezone: Annotated[
        str,
        cyclopts.Parameter(name="--timezone", help="时间窗所在时区，默认 UTC。"),
    ] = "UTC",
    min_rounds: Annotated[
        int,
        cyclopts.Parameter(name="--min-rounds", help="时间窗内用户消息数（不含开场白）至少达到此数才纳入。"),
    ] = 15,
    user_id: Annotated[
        Optional[str],
        cyclopts.Parameter(name="--user-id", help="仅保留该 user_id（与 agent_id 同时指定则只查单会话）。"),
    ] = None,
    agent_id: Annotated[
        Optional[str],
        cyclopts.Parameter(name="--agent-id", help="仅保留该 agent_id。"),
    ] = None,
    output_json: Annotated[
        Optional[str],
        cyclopts.Parameter(name="--output-json", help="将结果写入该 JSON 文件。"),
    ] = None,
    include_messages: Annotated[
        bool,
        cyclopts.Parameter(name="--include-messages", help="为每个匹配对拉取完整消息列表并写入输出。"),
    ] = False,
    config: Annotated[
        Optional[str],
        cyclopts.Parameter(name="--config", help="复制此 YAML 到当前目录 config.yaml 后再导入 app；不指定则要求已存在 config.yaml。"),
    ] = None,
    no_replica: Annotated[
        bool,
        cyclopts.Parameter(
            name="--no-replica",
            help="改为主库读取；不传则默认从只读副本读取（需 config 配置 replica_host）。",
        ),
    ] = False,
) -> None:
    """按日期与可选条件查询 chat_history，输出匹配对及可选消息。默认读副本。"""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    use_replica = not no_replica

    logger.info("Checking config...")
    _ensure_config(config)
    logger.info("Config ready (config.yaml in cwd)")

    # 导入依赖 config 的 app
    logger.info("Loading app modules...")
    from app.core.config import global_config_loaded_from_config_yaml
    from app.services.chat_history_service import (
        _sync_url_from_async_replica,
        get_chat_history_replica_connection,
    )
    from app.services.festival_memory_service import (
        _window_for_festival_date,
        get_messages_for_user_agent_sync,
        get_pairs_with_min_rounds_in_window_sync,
    )

    replica_conn = None
    if use_replica:
        logger.info("Using read replica (replica_host/replica_port from config)")
        async_replica_url = global_config_loaded_from_config_yaml.database.async_replica_url
        if not async_replica_url:
            print(
                "错误: 已指定从副本读取但 config 未配置 replica_host/replica_port，请检查 config.yaml 或使用 --no-replica",
                file=sys.stderr,
            )
            sys.exit(1)
        db_url = _sync_url_from_async_replica(async_replica_url)
        replica_conn = get_chat_history_replica_connection()
        logger.info("Replica connection established")
    else:
        logger.info("Using primary DB (--no-replica)")
        db_url = global_config_loaded_from_config_yaml.database.url

    # 解析日期
    try:
        parsed_date = date.fromisoformat(date_arg)
    except ValueError:
        print(f"错误: 无效日期 {date_arg!r}，应为 YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)

    window_start, window_end = _window_for_festival_date(parsed_date, timezone)
    logger.info(
        "Time window: %s to %s (timezone=%s, min_rounds=%s)",
        window_start.isoformat(),
        window_end.isoformat(),
        timezone,
        min_rounds,
    )

    logger.info("Querying (user_id, agent_id) pairs in window...")
    pairs = get_pairs_with_min_rounds_in_window_sync(
        parsed_date,
        db_url,
        min_rounds=min_rounds,
        timezone_str=timezone,
    )
    logger.info("Found %s pairs in window", len(pairs))

    if user_id is not None or agent_id is not None:
        before = len(pairs)
        pairs = [
            (uid, aid)
            for uid, aid in pairs
            if (user_id is None or uid == user_id) and (agent_id is None or aid == agent_id)
        ]
        logger.info("After filter (user_id=%s, agent_id=%s): %s -> %s pairs", user_id, agent_id, before, len(pairs))

    logger.info("Fetching user and agent names...")
    user_id_to_name, agent_id_to_name = _fetch_user_and_agent_names(
        pairs, replica_conn, db_url
    )

    entries: list[dict] = []
    total_messages = 0
    if include_messages:
        logger.info("Fetching messages for %s pairs...", len(pairs))
    for idx, (uid, aid) in enumerate(pairs):
        entry: dict = {
            "user_id": uid,
            "agent_id": aid,
            "user_name": user_id_to_name.get(uid),
            "agent_name": agent_id_to_name.get(aid),
        }
        if include_messages:
            messages = get_messages_for_user_agent_sync(uid, aid, connection=replica_conn)
            entry["messages"] = [{"role": r, "content": c} for r, c in messages]
            total_messages += len(messages)
            if (idx + 1) % 50 == 0 or idx + 1 == len(pairs):
                logger.info("Messages fetched for %s/%s pairs (%s messages so far)", idx + 1, len(pairs), total_messages)
        entries.append(entry)

    logger.info("Building result (pairs=%s)", len(entries))
    result = {
        "query": {
            "date": date_arg,
            "timezone": timezone,
            "min_rounds": min_rounds,
            "user_id": user_id,
            "agent_id": agent_id,
            "replica": use_replica,
        },
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "pairs": entries,
    }

    if output_json:
        out_path = Path(output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Writing JSON to %s", out_path)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"已写入 {len(pairs)} 个匹配对到 {out_path}")

    logger.info("Done.")
    print(f"匹配 (user_id, agent_id) 对数: {len(pairs)}")
    if include_messages:
        print(f"总消息条数: {total_messages}")


if __name__ == "__main__":
    app = cyclopts.App(help="按日期与条件查询 chat_history，复用节日记忆时间窗与消息拉取逻辑。")
    app.default(main)
    app()
