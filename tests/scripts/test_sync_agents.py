import os
import uuid
from pathlib import Path

import psycopg
from psycopg import sql
import pytest
import yaml
from sqlalchemy.ext.asyncio import create_async_engine

from scripts.sync_agents_dev_to_prod.sync_agents import (
    create_db_url,
    get_engine_kwargs,
    load_env_database_config,
    test_connection,
)


def _postgres_admin_params() -> dict:
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", ""),
        "dbname": os.getenv("POSTGRES_DB", "postgres"),
    }


def _ensure_can_connect(params: dict) -> bool:
    try:
        with psycopg.connect(**params) as conn:
            conn.execute("SELECT 1")
        return True
    except psycopg.OperationalError:
        return False


def _drop_and_create_database(params: dict, database_name: str) -> None:
    admin_params = params.copy()
    admin_params["dbname"] = params["dbname"]
    with psycopg.connect(**admin_params, autocommit=True) as conn:
        conn.execute(
            sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database_name))
        )
        conn.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name))
        )


def _drop_database(params: dict, database_name: str) -> None:
    admin_params = params.copy()
    admin_params["dbname"] = params["dbname"]
    with psycopg.connect(**admin_params, autocommit=True) as conn:
        conn.execute(
            sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database_name))
        )


def _write_env_config(path: Path, params: dict, database_name: str) -> None:
    config = {
        "database": {
            "host": params["host"],
            "port": params["port"],
            "user": params["user"],
            "password": params["password"],
            "db": database_name,
        }
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")


@pytest.mark.asyncio
async def test_load_env_database_config_reads_devops_files(tmp_path, monkeypatch):
    admin_params = _postgres_admin_params()
    if not _ensure_can_connect(admin_params):
        pytest.skip("本地 Postgres 未在 localhost:5432 启动，跳过同步脚本集成测试")

    dev_db_name = f"sync_agents_dev_{uuid.uuid4().hex[:8]}"
    prod_db_name = f"sync_agents_prod_{uuid.uuid4().hex[:8]}"

    _drop_and_create_database(admin_params, dev_db_name)
    _drop_and_create_database(admin_params, prod_db_name)

    devops_dir = tmp_path / "devops"
    _write_env_config(devops_dir / "config.yaml.dev", admin_params, dev_db_name)
    _write_env_config(devops_dir / "config.yaml.prod", admin_params, prod_db_name)

    monkeypatch.chdir(tmp_path)

    dev_config = load_env_database_config("devops/config.yaml.dev", "Dev")
    prod_config = load_env_database_config("devops/config.yaml.prod", "Prod")

    dev_engine = create_async_engine(
        create_db_url(dev_config), echo=False, **get_engine_kwargs(dev_config)
    )
    prod_engine = create_async_engine(
        create_db_url(prod_config), echo=False, **get_engine_kwargs(prod_config)
    )

    try:
        assert dev_config["db"] == dev_db_name
        assert prod_config["db"] == prod_db_name
        assert await test_connection(dev_engine, "Dev")
        assert await test_connection(prod_engine, "Prod")
    finally:
        await dev_engine.dispose()
        await prod_engine.dispose()
        _drop_database(admin_params, dev_db_name)
        _drop_database(admin_params, prod_db_name)
