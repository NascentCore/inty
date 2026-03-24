from __future__ import annotations

from .sqlite_db import SQLiteDatabase, to_iso, utc_now


class CursorRepository:
    def __init__(self, db: SQLiteDatabase) -> None:
        self._db = db

    def get_cursor(self, *, cursor_key: str) -> str | None:
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT cursor_value FROM cursors WHERE cursor_key = ?",
                (cursor_key,),
            ).fetchone()
            if row is None:
                return None
            return str(row["cursor_value"])

    def set_cursor(self, *, cursor_key: str, cursor_value: str) -> None:
        with self._db.connect() as conn:
            conn.execute(
                """
                INSERT INTO cursors(cursor_key, cursor_value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(cursor_key) DO UPDATE SET
                    cursor_value = excluded.cursor_value,
                    updated_at = excluded.updated_at
                """,
                (cursor_key, cursor_value, to_iso(utc_now())),
            )
