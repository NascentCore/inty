from __future__ import annotations

from datetime import datetime, timedelta

from .sqlite_db import SQLiteDatabase, to_iso, utc_now


class LeaseRepository:
    def __init__(self, db: SQLiteDatabase) -> None:
        self._db = db

    def try_acquire_or_renew(
        self,
        *,
        lease_key: str,
        owner_id: str,
        ttl_seconds: int,
        now: datetime | None = None,
    ) -> bool:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be > 0")
        now_dt = now or utc_now()
        expires_at = now_dt + timedelta(seconds=ttl_seconds)
        with self._db.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    """
                    SELECT owner_id, expires_at
                    FROM consumer_leases
                    WHERE lease_key = ?
                    """,
                    (lease_key,),
                ).fetchone()
                if row is None:
                    conn.execute(
                        """
                        INSERT INTO consumer_leases(lease_key, owner_id, expires_at, updated_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            lease_key,
                            owner_id,
                            to_iso(expires_at),
                            to_iso(now_dt),
                        ),
                    )
                    conn.execute("COMMIT")
                    return True
                current_owner = str(row["owner_id"])
                current_expires_at = datetime.fromisoformat(
                    str(row["expires_at"])
                )
                can_take = (
                    current_owner == owner_id or current_expires_at <= now_dt
                )
                if not can_take:
                    conn.execute("COMMIT")
                    return False
                conn.execute(
                    """
                    UPDATE consumer_leases
                    SET owner_id = ?, expires_at = ?, updated_at = ?
                    WHERE lease_key = ?
                    """,
                    (owner_id, to_iso(expires_at), to_iso(now_dt), lease_key),
                )
                conn.execute("COMMIT")
                return True
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def release_if_owner(self, *, lease_key: str, owner_id: str) -> bool:
        with self._db.connect() as conn:
            cursor = conn.execute(
                """
                DELETE FROM consumer_leases
                WHERE lease_key = ? AND owner_id = ?
                """,
                (lease_key, owner_id),
            )
            return cursor.rowcount > 0
