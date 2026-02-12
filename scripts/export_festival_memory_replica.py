#!/usr/bin/env python3
"""
从 inty 生产只读副本导出指定节日记忆到 JSON 文件。

连接配置默认从 devops/config.yaml.prod 读取（replica_host/replica_port），
可通过环境变量覆盖：DB_REPLICA_HOST, DB_REPLICA_PORT, DB_USER, DB_PASSWORD, DB_NAME。
副本公网 IP 可用时设置 DB_REPLICA_HOST=34.87.163.31；否则需在能访问副本内网的环境运行（同 VPC 或 VPN）。

用法:
    export PYTHONPATH=.
    python scripts/export_festival_memory_replica.py
    python scripts/export_festival_memory_replica.py --config devops/config.yaml.prod --output festival_memory_christmas_2026.json
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Any, Optional

import cyclopts
import psycopg2
import yaml

logger = logging.getLogger(__name__)

# 与用户提供的 SQL 完全一致
FESTIVAL_MEMORY_SQL = """
SELECT *
FROM memory
WHERE memory_type = 'festival'
  AND festival_name = 'Christmas 2026 🎅'
  AND festival_date = DATE '2025-12-25'
ORDER BY extracted_at DESC;
"""

DEFAULT_CONFIG_PATH = "devops/config.yaml.prod"
DEFAULT_OUTPUT = "festival_memory_christmas_2026.json"


def _repo_root() -> Path:
    """仓库根目录（scripts 的上一级）。"""
    return Path(__file__).resolve().parent.parent


def load_replica_config(config_path: Optional[str]) -> dict[str, Any]:
    """
    从 YAML 加载 database 配置，并强制使用副本 host/port；环境变量可覆盖。
    返回用于 psycopg2.connect 的参数字典：host, port, user, password, dbname。
    """
    path = Path(config_path) if config_path else _repo_root() / DEFAULT_CONFIG_PATH
    db_config: dict[str, Any] = {
        "host": "localhost",
        "port": 5432,
        "user": "postgres",
        "password": "",
        "dbname": "inty",
    }
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            db_section = config.get("database", {}) or {}
            db_config["host"] = db_section.get("replica_host") or db_section.get("host") or db_config["host"]
            db_config["port"] = db_section.get("replica_port") or db_section.get("port") or db_config["port"]
            # 与 host/port 一致：优先使用副本专用凭证，再回退到主库 user/password
            db_config["user"] = db_section.get("replica_user") or db_section.get("user") or db_config["user"]
            db_config["password"] = db_section.get("replica_password") or db_section.get("password") or db_config["password"]
            db_config["dbname"] = db_section.get("db") or db_config["dbname"]
            logger.debug("从配置文件加载数据库配置: %s", path)
        except Exception as e:
            logger.warning("读取配置文件失败: %s", e)
    else:
        logger.warning("配置文件不存在: %s，使用默认与环境变量", path)

    # 环境变量覆盖
    db_config["host"] = os.getenv("DB_REPLICA_HOST", db_config["host"])
    db_config["port"] = int(os.getenv("DB_REPLICA_PORT", str(db_config["port"])))
    db_config["user"] = os.getenv("DB_USER", db_config["user"])
    db_config["password"] = os.getenv("DB_PASSWORD", db_config["password"])
    db_config["dbname"] = os.getenv("DB_NAME", db_config["dbname"])

    return db_config


def _row_to_json_serializable(row: tuple, columns: list[str]) -> dict[str, Any]:
    """将 psycopg2 返回的一行转为可 JSON 序列化的 dict（date/datetime 转 ISO 字符串）。"""
    out: dict[str, Any] = {}
    for i, col in enumerate(columns):
        val = row[i] if i < len(row) else None
        if isinstance(val, (datetime, date)):
            out[col] = val.isoformat()
        else:
            out[col] = val
    return out


def run(
    config: Optional[str] = None,
    output: Optional[str] = None,
) -> None:
    """
    连接 inty 副本，执行节日记忆 SQL，将结果写入 JSON 文件。
    """
    cfg = load_replica_config(config)
    out_path = Path(output) if output else _repo_root() / DEFAULT_OUTPUT
    out_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("连接副本 %s:%s 数据库 %s", cfg["host"], cfg["port"], cfg["dbname"])
    conn = psycopg2.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        dbname=cfg["dbname"],
        connect_timeout=10,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(FESTIVAL_MEMORY_SQL)
            columns = [d.name for d in cur.description]
            rows = cur.fetchall()
        conn.close()
    except Exception as e:
        conn.close()
        raise RuntimeError(f"查询副本失败: {e}") from e

    payload = [_row_to_json_serializable(r, columns) for r in rows]
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    logger.info("已写入 %d 条记录到 %s", len(payload), out_path)


def main(
    config: Annotated[
        Optional[str],
        cyclopts.Parameter(
            help="数据库配置文件路径，默认 devops/config.yaml.prod（使用副本）。",
        ),
    ] = None,
    output: Annotated[
        Optional[str],
        cyclopts.Parameter(
            help="输出 JSON 文件路径，默认 festival_memory_christmas_2026.json。",
        ),
    ] = None,
) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run(config=config, output=output)


if __name__ == "__main__":
    cyclopts.run(main)
