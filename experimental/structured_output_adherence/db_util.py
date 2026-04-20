from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
import yaml
from psycopg2.extensions import connection as PgConnection


def session_id_for_chat(chat_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, chat_id))


def load_db_config(
    config_path: Optional[str], database_url: Optional[str]
) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Returns (database_url_or_none, kwargs_for_psycopg2_connect).
    If database_url is set from arg or env DATABASE_URL, kwargs are empty.
    """
    if database_url:
        return database_url, {}
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url, {}

    path = config_path or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.yaml"
    )
    db_kwargs: Dict[str, Any] = {}
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        db = cfg.get("database") or {}
        db_kwargs = {
            "host": os.getenv("DB_HOST", db.get("host", "localhost")),
            "port": int(os.getenv("DB_PORT", db.get("port", 5432))),
            "user": os.getenv("DB_USER", db.get("user", "postgres")),
            "password": os.getenv("DB_PASSWORD", db.get("password", "")),
            "dbname": os.getenv("DB_NAME", db.get("db", "inty")),
        }
    else:
        db_kwargs = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD", ""),
            "dbname": os.getenv("DB_NAME", "inty"),
        }
    return None, db_kwargs


def connect_db(config_path: Optional[str], database_url: Optional[str]) -> PgConnection:
    url, kwargs = load_db_config(config_path, database_url)
    if url:
        return psycopg2.connect(url)
    return psycopg2.connect(**kwargs)


@dataclass
class HistoryRow:
    message: Any
    created_at: datetime


def fetch_random_active_chat_ids(conn: PgConnection, pool: int) -> List[str]:
    q = """
        SELECT id FROM chats
        WHERE is_active = true
        ORDER BY random()
        LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(q, (pool,))
        return [r[0] for r in cur.fetchall()]


def count_history_rows(
    conn: PgConnection,
    session_id: str,
    since: Optional[datetime],
    until: Optional[datetime],
) -> int:
    clauses = ["session_id = %s::uuid", "deleted_at IS NULL"]
    params: List[Any] = [session_id]
    if since is not None:
        clauses.append("created_at >= %s")
        params.append(since)
    if until is not None:
        clauses.append("created_at < %s")
        params.append(until)
    q = f"SELECT COUNT(*) FROM chat_history WHERE {' AND '.join(clauses)}"
    with conn.cursor() as cur:
        cur.execute(q, tuple(params))
        row = cur.fetchone()
        return int(row[0]) if row else 0


def load_chat_history(
    conn: PgConnection,
    session_id: str,
    since: Optional[datetime],
    until: Optional[datetime],
) -> List[HistoryRow]:
    clauses = ["session_id = %s::uuid", "deleted_at IS NULL"]
    params: List[Any] = [session_id]
    if since is not None:
        clauses.append("created_at >= %s")
        params.append(since)
    if until is not None:
        clauses.append("created_at < %s")
        params.append(until)
    q = f"""
        SELECT message, created_at
        FROM chat_history
        WHERE {' AND '.join(clauses)}
        ORDER BY created_at ASC
    """
    with conn.cursor() as cur:
        cur.execute(q, tuple(params))
        rows = cur.fetchall()
    out: List[HistoryRow] = []
    for message, created_at in rows:
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        out.append(HistoryRow(message=message, created_at=created_at))
    return out
