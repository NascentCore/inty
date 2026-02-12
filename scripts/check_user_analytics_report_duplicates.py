#!/usr/bin/env python3
"""
在本地连接生产只读副本，检查 user_analytics_report 表中是否存在重复的 (report_type, report_date)。

用于验证 MultipleResultsFound 根因：若存在多行则与生产 inty-dev 现象一致。
连接配置从 devops/config.yaml.prod 读取（replica_host/replica_port），数据库名默认 inty-dev（与生产一致），
可用环境变量覆盖：DB_REPLICA_HOST, DB_REPLICA_PORT, DB_USER, DB_PASSWORD, DB_NAME。

用法（仓库根目录）:
    export PYTHONPATH=.
    python scripts/check_user_analytics_report_duplicates.py
    python scripts/check_user_analytics_report_duplicates.py --config devops/config.yaml.prod --db inty-dev
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Any, Optional

import cyclopts
import psycopg2
import yaml

DEFAULT_CONFIG_PATH = "devops/config.yaml.prod"
DEFAULT_DB = "inty-dev"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_replica_config(
    config_path: Optional[str], dbname_override: Optional[str] = None
) -> dict[str, Any]:
    """
    从 YAML 加载 database 配置，使用副本 host/port；环境变量可覆盖。
    返回用于 psycopg2.connect 的参数字典。
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
            db_config["host"] = (
                db_section.get("replica_host") or db_section.get("host") or db_config["host"]
            )
            db_config["port"] = (
                db_section.get("replica_port") or db_section.get("port") or db_config["port"]
            )
            db_config["user"] = db_section.get("replica_user") or db_section.get("user") or db_config["user"]
            db_config["password"] = (
                db_section.get("replica_password") or db_section.get("password") or db_config["password"]
            )
            db_config["dbname"] = db_section.get("db") or db_config["dbname"]
        except Exception as e:
            print(f"读取配置文件失败: {path} - {e}")
    if dbname_override:
        db_config["dbname"] = dbname_override
    db_config["host"] = os.getenv("DB_REPLICA_HOST", db_config["host"])
    db_config["port"] = int(os.getenv("DB_REPLICA_PORT", str(db_config["port"])))
    db_config["user"] = os.getenv("DB_USER", db_config["user"])
    db_config["password"] = os.getenv("DB_PASSWORD", db_config["password"])
    db_config["dbname"] = os.getenv("DB_NAME", db_config["dbname"])
    return db_config


def run(
    config: Annotated[
        Optional[str],
        cyclopts.Parameter(name="--config", help="config YAML 路径，默认 devops/config.yaml.prod"),
    ] = None,
    db: Annotated[
        Optional[str],
        cyclopts.Parameter(name="--db", help="数据库名，默认 inty-dev（与生产一致）"),
    ] = None,
) -> None:
    cfg = load_replica_config(
        config, dbname_override=(db if db is not None else DEFAULT_DB)
    )
    print(f"连接副本 {cfg['host']}:{cfg['port']} 数据库 {cfg['dbname']} ...")
    try:
        conn = psycopg2.connect(
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password=cfg["password"],
            dbname=cfg["dbname"],
            connect_timeout=10,
        )
    except Exception as e:
        print(f"连接失败: {e}")
        return
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT report_type, report_date, COUNT(*) AS cnt
                FROM user_analytics_report
                GROUP BY report_type, report_date
                HAVING COUNT(*) > 1
                ORDER BY report_date DESC
            """)
            rows = cur.fetchall()
        if not rows:
            print("未发现重复的 (report_type, report_date)。")
            return
        print(f"发现 {len(rows)} 组重复的 (report_type, report_date):")
        for report_type, report_date, cnt in rows:
            print(f"  {report_type}  {report_date}  cnt={cnt}")
        print("\n示例：查看某日日报多行（将 2026-02-12 换成上面出现的日期）:")
        print("  SELECT id, report_type, report_date, created_at")
        print("  FROM user_analytics_report")
        print("  WHERE report_type = 'daily' AND report_date = '2026-02-12'")
        print("  ORDER BY created_at;")
    finally:
        conn.close()


if __name__ == "__main__":
    cyclopts.run(run)
