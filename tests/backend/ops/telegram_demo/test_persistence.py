"""Tests for telegram-demo Postgres persistence."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete

from app.db.session import AsyncSessionLocal, async_engine
from app.models.chat import Chat
from app.models.ops_telegram_demo import (
    OpsTelegramDemoBinding,
    OpsTelegramDemoPollState,
)
from app.models.registry import load_model_modules
from backend.ops.telegram_demo.binding import TelegramDemoBinding
from backend.ops.telegram_demo.persistence import (
    delete_binding,
    list_bindings,
    load_poll_offset,
    save_poll_offset,
    upsert_binding,
)
from backend.ops.telegram_demo.provision import provision_inty_for_telegram_onboard


@pytest.fixture(autouse=True)
async def _dispose_shared_engine_after_test() -> None:
    yield
    await async_engine.dispose()


@pytest.mark.asyncio
async def test_upsert_list_delete_binding() -> None:
    load_model_modules()
    telegram_chat_id = f"tg-persist-{uuid.uuid4().hex}"
    await async_engine.dispose()
    provision = await provision_inty_for_telegram_onboard(
        telegram_chat_id=telegram_chat_id,
    )
    binding = TelegramDemoBinding(
        telegram_chat_id=telegram_chat_id,
        user_id=provision.user_id,
        agent_id=provision.agent_id,
        chat_id=provision.chat_id,
    )

    await upsert_binding(binding)
    rows = await list_bindings()
    match = [r for r in rows if r.telegram_chat_id == telegram_chat_id]
    assert len(match) == 1
    assert match[0].user_id == provision.user_id

    updated = TelegramDemoBinding(
        telegram_chat_id=telegram_chat_id,
        user_id=provision.user_id,
        agent_id=provision.agent_id,
        chat_id=provision.chat_id,
    )
    await upsert_binding(updated)
    rows = await list_bindings()
    match = [r for r in rows if r.telegram_chat_id == telegram_chat_id]
    assert match[0].agent_id == provision.agent_id

    await delete_binding(telegram_chat_id)
    rows = await list_bindings()
    assert telegram_chat_id not in {r.telegram_chat_id for r in rows}

    async with AsyncSessionLocal() as db:
        await db.execute(delete(Chat).where(Chat.user_id == provision.user_id))
        await db.execute(
            delete(OpsTelegramDemoBinding).where(
                OpsTelegramDemoBinding.telegram_chat_id == telegram_chat_id
            )
        )
        await db.commit()


@pytest.mark.asyncio
async def test_poll_offset_roundtrip() -> None:
    load_model_modules()
    async with AsyncSessionLocal() as db:
        row = await db.get(OpsTelegramDemoPollState, 1)
        if row is not None:
            row.last_update_id = None
            await db.commit()

    assert await load_poll_offset() is None
    await save_poll_offset(42)
    assert await load_poll_offset() == 42
    await save_poll_offset(99)
    assert await load_poll_offset() == 99

    async with AsyncSessionLocal() as db:
        row = await db.get(OpsTelegramDemoPollState, 1)
        assert row is not None
        row.last_update_id = None
        await db.commit()
