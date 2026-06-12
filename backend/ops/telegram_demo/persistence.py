"""Postgres persistence for Ops telegram-demo bindings and poll offset."""

from __future__ import annotations

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.ops_telegram_demo import (
    OpsTelegramDemoBinding,
    OpsTelegramDemoPollState,
)
from backend.ops.telegram_demo.binding import TelegramDemoBinding

_POLL_STATE_ROW_ID = 1


class PersistedTelegramBinding(BaseModel):
    """Serializable binding row for restore after Ops restart."""

    telegram_chat_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    chat_id: str = Field(min_length=1)

    model_config = ConfigDict(from_attributes=True)

    def to_demo_binding(self) -> TelegramDemoBinding:
        return TelegramDemoBinding(
            telegram_chat_id=self.telegram_chat_id,
            user_id=self.user_id,
            agent_id=self.agent_id,
            chat_id=self.chat_id,
        )


def _binding_from_row(row: OpsTelegramDemoBinding) -> PersistedTelegramBinding:
    return PersistedTelegramBinding.model_validate(row)


async def upsert_binding(binding: TelegramDemoBinding) -> None:
    assert binding.telegram_chat_id != ""
    payload = PersistedTelegramBinding(
        telegram_chat_id=binding.telegram_chat_id,
        user_id=binding.user_id,
        agent_id=binding.agent_id,
        chat_id=binding.chat_id,
    ).model_dump()
    async with AsyncSessionLocal() as db:
        row = await db.get(OpsTelegramDemoBinding, binding.telegram_chat_id)
        if row is None:
            db.add(OpsTelegramDemoBinding(**payload))
        else:
            row.user_id = binding.user_id
            row.agent_id = binding.agent_id
            row.chat_id = binding.chat_id
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception(
                "telegram-demo binding persist failed chat_id={}",
                binding.telegram_chat_id,
            )
            raise


# TODO(telegram-demo-unbind): Wire to transport unbind + stop presence — #3340
async def delete_binding(telegram_chat_id: str) -> None:
    assert telegram_chat_id != ""
    async with AsyncSessionLocal() as db:
        row = await db.get(OpsTelegramDemoBinding, telegram_chat_id)
        if row is not None:
            await db.delete(row)
            await db.commit()


async def list_bindings() -> list[PersistedTelegramBinding]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(OpsTelegramDemoBinding).order_by(
                OpsTelegramDemoBinding.telegram_chat_id
            )
        )
        return [_binding_from_row(row) for row in result.scalars().all()]


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
