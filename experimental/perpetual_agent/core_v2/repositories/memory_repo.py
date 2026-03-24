from __future__ import annotations

import json
import sqlite3

from ..contracts import MemoryItem
from .sqlite_db import SQLiteDatabase, from_iso, to_iso, utc_now


class MemoryRepository:
    def __init__(self, db: SQLiteDatabase) -> None:
        self._db = db

    def upsert_memory(self, item: MemoryItem) -> None:
        with self._db.connect() as conn:
            conn.execute(
                """
                INSERT INTO memory_items(
                    memory_id,
                    user_id,
                    memory_type,
                    key,
                    value,
                    confidence,
                    evidence_event_ids_json,
                    status,
                    first_seen_at,
                    last_seen_at,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(memory_id) DO UPDATE SET
                    value = excluded.value,
                    confidence = excluded.confidence,
                    evidence_event_ids_json = excluded.evidence_event_ids_json,
                    status = excluded.status,
                    last_seen_at = excluded.last_seen_at
                """,
                (
                    item.memory_id,
                    item.user_id,
                    item.memory_type.value,
                    item.key,
                    item.value,
                    item.confidence,
                    json.dumps(item.evidence_event_ids, ensure_ascii=False),
                    item.status.value,
                    to_iso(item.first_seen_at),
                    to_iso(item.last_seen_at),
                    to_iso(utc_now()),
                ),
            )

    def list_memories_by_user(self, *, user_id: str, limit: int = 200) -> list[MemoryItem]:
        with self._db.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    memory_id,
                    user_id,
                    memory_type,
                    key,
                    value,
                    confidence,
                    evidence_event_ids_json,
                    status,
                    first_seen_at,
                    last_seen_at
                FROM memory_items
                WHERE user_id = ?
                ORDER BY last_seen_at DESC, id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [self._row_to_model(row=row) for row in rows]

    @staticmethod
    def _row_to_model(*, row: sqlite3.Row) -> MemoryItem:
        return MemoryItem.model_validate(
            {
                "memory_id": row["memory_id"],
                "user_id": row["user_id"],
                "memory_type": row["memory_type"],
                "key": row["key"],
                "value": row["value"],
                "confidence": float(row["confidence"]),
                "evidence_event_ids": json.loads(row["evidence_event_ids_json"] or "[]"),
                "status": row["status"],
                "first_seen_at": from_iso(row["first_seen_at"]),
                "last_seen_at": from_iso(row["last_seen_at"]),
            }
        )
