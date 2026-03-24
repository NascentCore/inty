from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from ..contracts import InteractionEvent
from .sqlite_db import SQLiteDatabase, dumps_json, from_iso, to_iso, utc_now


class EventsRepository:
    def __init__(self, db: SQLiteDatabase) -> None:
        self._db = db

    def save_event_idempotent(self, event: InteractionEvent) -> bool:
        now = to_iso(utc_now())
        with self._db.connect() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO events(
                    event_id,
                    user_id,
                    channel,
                    direction,
                    content,
                    timestamp,
                    channel_message_id,
                    metadata_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.user_id,
                    event.channel.value,
                    event.direction.value,
                    event.content,
                    to_iso(event.timestamp),
                    event.channel_message_id,
                    dumps_json(event.metadata),
                    now,
                ),
            )
            return cursor.rowcount > 0

    def event_exists(self, event_id: str) -> bool:
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM events WHERE event_id = ? LIMIT 1",
                (event_id,),
            ).fetchone()
            return row is not None

    def delete_event(self, *, event_id: str) -> bool:
        with self._db.connect() as conn:
            cursor = conn.execute(
                "DELETE FROM events WHERE event_id = ?",
                (event_id,),
            )
            return cursor.rowcount > 0

    def list_events_since(self, since: datetime, limit: int = 100) -> list[InteractionEvent]:
        with self._db.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    event_id,
                    user_id,
                    channel,
                    direction,
                    content,
                    timestamp,
                    channel_message_id,
                    metadata_json
                FROM events
                WHERE timestamp >= ?
                ORDER BY timestamp ASC, id ASC
                LIMIT ?
                """,
                (to_iso(since), limit),
            ).fetchall()
        return [self._row_to_model(row=row) for row in rows]

    def list_events_by_user(self, user_id: str, limit: int = 100) -> list[InteractionEvent]:
        with self._db.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    event_id,
                    user_id,
                    channel,
                    direction,
                    content,
                    timestamp,
                    channel_message_id,
                    metadata_json
                FROM events
                WHERE user_id = ?
                ORDER BY timestamp ASC, id ASC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [self._row_to_model(row=row) for row in rows]

    @staticmethod
    def _row_to_model(*, row: sqlite3.Row) -> InteractionEvent:
        return InteractionEvent.model_validate(
            {
                "event_id": row["event_id"],
                "user_id": row["user_id"],
                "channel": row["channel"],
                "direction": row["direction"],
                "content": row["content"],
                "timestamp": from_iso(row["timestamp"]),
                "channel_message_id": row["channel_message_id"],
                "metadata": json.loads(row["metadata_json"] or "{}"),
            }
        )
