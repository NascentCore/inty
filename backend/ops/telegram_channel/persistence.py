"""Postgres persistence for Ops Telegram channel poll offset (bindings → agent_channel_endpoints)."""

from __future__ import annotations

from app.db.session import AsyncSessionLocal
from app.models.ops_telegram_demo import OpsTelegramDemoPollState

_POLL_STATE_ROW_ID = 1


async def load_poll_offset() -> int | None:
    async with AsyncSessionLocal() as db:
        row = await db.get(OpsTelegramDemoPollState, _POLL_STATE_ROW_ID)
        if row is None:
            return None
        raw = row.last_update_id
        if raw is None:
            return None
        return int(raw)


async def save_poll_offset(next_offset: int | None) -> None:
    async with AsyncSessionLocal() as db:
        row = await db.get(OpsTelegramDemoPollState, _POLL_STATE_ROW_ID)
        if row is None:
            db.add(
                OpsTelegramDemoPollState(
                    id=_POLL_STATE_ROW_ID,
                    last_update_id=next_offset,
                )
            )
        else:
            row.last_update_id = next_offset
        await db.commit()
