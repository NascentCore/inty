from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from ..contracts import ActionStatus, PlanAction
from .sqlite_db import SQLiteDatabase, from_iso, to_iso, utc_now


class PlanRepository:
    def __init__(self, db: SQLiteDatabase) -> None:
        self._db = db

    def save_action_idempotent(self, action: PlanAction) -> bool:
        now = to_iso(utc_now())
        with self._db.connect() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO plan_actions(
                    action_id,
                    user_id,
                    goal,
                    scheduled_at,
                    preferred_channel,
                    message_strategy,
                    constraints_json,
                    status,
                    result_event_id,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    action.action_id,
                    action.user_id,
                    action.goal,
                    to_iso(action.scheduled_at),
                    action.preferred_channel.value,
                    action.message_strategy,
                    json.dumps(action.constraints, ensure_ascii=False),
                    action.status.value,
                    action.result_event_id,
                    now,
                    now,
                ),
            )
            return cursor.rowcount > 0

    def list_due_actions(
        self, *, now: datetime, limit: int
    ) -> list[PlanAction]:
        with self._db.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    action_id,
                    user_id,
                    goal,
                    scheduled_at,
                    preferred_channel,
                    message_strategy,
                    constraints_json,
                    status,
                    result_event_id
                FROM plan_actions
                WHERE status = ? AND scheduled_at <= ?
                ORDER BY scheduled_at ASC, id ASC
                LIMIT ?
                """,
                (ActionStatus.PENDING.value, to_iso(now), limit),
            ).fetchall()
        return [self._row_to_model(row) for row in rows]

    def claim_action_running(self, *, action_id: str) -> bool:
        now = to_iso(utc_now())
        with self._db.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE plan_actions
                SET status = ?, updated_at = ?
                WHERE action_id = ? AND status = ?
                """,
                (
                    ActionStatus.RUNNING.value,
                    now,
                    action_id,
                    ActionStatus.PENDING.value,
                ),
            )
            return cursor.rowcount > 0

    def mark_done(self, *, action_id: str, result_event_id: str | None) -> bool:
        now = to_iso(utc_now())
        with self._db.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE plan_actions
                SET status = ?, result_event_id = ?, updated_at = ?
                WHERE action_id = ? AND status IN (?, ?)
                """,
                (
                    ActionStatus.DONE.value,
                    result_event_id,
                    now,
                    action_id,
                    ActionStatus.RUNNING.value,
                    ActionStatus.PENDING.value,
                ),
            )
            return cursor.rowcount > 0

    def mark_failed(self, *, action_id: str) -> bool:
        now = to_iso(utc_now())
        with self._db.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE plan_actions
                SET status = ?, updated_at = ?
                WHERE action_id = ? AND status IN (?, ?)
                """,
                (
                    ActionStatus.FAILED.value,
                    now,
                    action_id,
                    ActionStatus.RUNNING.value,
                    ActionStatus.PENDING.value,
                ),
            )
            return cursor.rowcount > 0

    def delete_action(self, *, action_id: str) -> bool:
        with self._db.connect() as conn:
            cursor = conn.execute(
                "DELETE FROM plan_actions WHERE action_id = ?",
                (action_id,),
            )
            return cursor.rowcount > 0

    @staticmethod
    def _row_to_model(row: sqlite3.Row) -> PlanAction:
        return PlanAction.model_validate(
            {
                "action_id": row["action_id"],
                "user_id": row["user_id"],
                "goal": row["goal"],
                "scheduled_at": from_iso(row["scheduled_at"]),
                "preferred_channel": row["preferred_channel"],
                "message_strategy": row["message_strategy"],
                "constraints": json.loads(row["constraints_json"] or "{}"),
                "status": row["status"],
                "result_event_id": row["result_event_id"],
            }
        )
