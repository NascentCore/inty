from __future__ import annotations

from .sqlite_db import SQLiteDatabase


def init_schema(db: SQLiteDatabase) -> None:
    with db.connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                user_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                direction TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                channel_message_id TEXT,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_events_user_time
            ON events(user_id, timestamp)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_id TEXT NOT NULL UNIQUE,
                user_id TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence REAL NOT NULL,
                evidence_event_ids_json TEXT NOT NULL,
                status TEXT NOT NULL,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_memory_items_user_type_key
            ON memory_items(user_id, memory_type, key)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS plan_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_id TEXT NOT NULL UNIQUE,
                user_id TEXT NOT NULL,
                goal TEXT NOT NULL,
                scheduled_at TEXT NOT NULL,
                preferred_channel TEXT NOT NULL,
                message_strategy TEXT NOT NULL,
                constraints_json TEXT NOT NULL,
                status TEXT NOT NULL,
                result_event_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_plan_actions_status_scheduled
            ON plan_actions(status, scheduled_at)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS consumer_leases (
                lease_key TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cursors (
                cursor_key TEXT PRIMARY KEY,
                cursor_value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
