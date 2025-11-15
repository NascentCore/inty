import os
import subprocess
import sys
import uuid
from pathlib import Path

import psycopg2
from psycopg2 import sql
import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
BASE_CONFIG_PATH = REPO_ROOT / "devops" / "config.yaml.test"


def _postgres_params() -> dict:
    return {
        "user": os.getenv("PG_USER", "postgres"),
        "password": os.getenv("PG_PASSWORD", "sxwl666!"),
        "host": os.getenv("PG_HOST", "localhost"),
        "port": int(os.getenv("PG_PORT", "5432")),
    }


def _admin_connection():
    maintenance_candidates = [
        os.getenv("PG_MAINTENANCE_DB"),
        "postgres",
        os.getenv("PG_DB"),
        "inty",
    ]
    params = _postgres_params()
    last_exc = None
    for dbname in maintenance_candidates:
        if not dbname:
            continue
        try:
            conn = psycopg2.connect(dbname=dbname, **params)
            conn.autocommit = True
            return conn
        except psycopg2.OperationalError as exc:
            last_exc = exc
    pytest.skip(f"无法连接 Postgres 管理库: {last_exc}")


def _recreate_database(dbname: str):
    conn = _admin_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = %s
                """,
                (dbname,),
            )
            cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(dbname)))
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))
    finally:
        conn.close()


def _drop_database(dbname: str):
    conn = _admin_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = %s
                """,
                (dbname,),
            )
            cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(dbname)))
    finally:
        conn.close()


def _write_custom_config(path: Path, dbname: str) -> Path:
    if not BASE_CONFIG_PATH.exists():
        pytest.skip("缺少 devops/config.yaml.test，无法生成 Alembic 测试配置")

    config_data = yaml.safe_load(BASE_CONFIG_PATH.read_text(encoding="utf-8"))
    database_cfg = config_data.setdefault("database", {})
    params = _postgres_params()
    database_cfg.update(
        {
            "db": dbname,
            "host": params["host"],
            "port": params["port"],
            "user": params["user"],
            "password": params["password"],
        }
    )

    path.write_text(yaml.safe_dump(config_data), encoding="utf-8")
    return path


def _fetch_alembic_version(dbname: str) -> str | None:
    params = _postgres_params()
    with psycopg2.connect(dbname=dbname, **params) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version_num FROM alembic_version LIMIT 1")
            row = cur.fetchone()
            return row[0] if row else None


@pytest.mark.integration
def test_alembic_upgrade_uses_custom_config(tmp_path):
    """验证 Alembic env.py 会使用 -x config=... 指定的配置连接数据库。"""

    db_name = f"alembic_test_{uuid.uuid4().hex[:8]}"
    config_path = tmp_path / "config.yaml"
    _recreate_database(db_name)
    _write_custom_config(config_path, db_name)

    env = os.environ.copy()
    existing_path = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{REPO_ROOT}:{existing_path}" if existing_path else str(REPO_ROOT)
    )

    cmd = [
        sys.executable,
        "-m",
        "alembic",
        "-c",
        "alembic.ini",
        "upgrade",
        "head",
        "-x",
        f"config={config_path}",
    ]

    try:
        completed = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        version = _fetch_alembic_version(db_name)
        assert (
            version is not None
        ), f"Alembic 未在自定义数据库内记录版本，stdout={completed.stdout}, stderr={completed.stderr}"
    finally:
        _drop_database(db_name)
