"""Tests for inner-tick scope resolution (legacy chats.id vs agent-scope key)."""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import delete

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.uuid import get_new_user_id
from app.db.session import AsyncSessionLocal, async_engine
from app.models.registry import load_model_modules
from app.models.user import AuthType, User
from app.services.agentic_companion.inner_tick_delivery import (
    inner_tick_delivery_for_telegram,
)
from app.services.agentic_companion.inner_tick_fire import (
    InnerTickFireInput,
    InnerTickModelSource,
    _resolve_inner_tick_scope_coords,
)
from app.services.agentic_companion.session import Coordinator, InnerTickCoords


async def _create_guest_user() -> User:
    async with AsyncSessionLocal() as db:
        user_id = get_new_user_id()
        user = User(
            id=user_id,
            auth_type=AuthType.GUEST,
            nickname="inner_tick_test",
            meta_data={"test": True},
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


async def _delete_user(user_id: str) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


@pytest.fixture(autouse=True)
async def _dispose_engine() -> None:
    load_model_modules()
    await async_engine.dispose()
    yield
    await async_engine.dispose()


@pytest.mark.asyncio
async def test_resolve_inner_tick_scope_coords_accepts_agent_scope_chat_id() -> None:
    user = await _create_guest_user()
    agent_id = "agent-inner-tick-test"
    scope = AgentScope(user_id=user.id, agent_id=agent_id)
    coordinator = Coordinator.for_loop(asyncio.get_running_loop())

    async def _noop(_text: str) -> None:
        return None

    fire_input = InnerTickFireInput(
        delivery=inner_tick_delivery_for_telegram(_noop),
        coords=InnerTickCoords(
            user_id=user.id,
            agent_id=agent_id,
            chat_id=scope.memory_store_chat_id(),
        ),
        coordinator=coordinator,
        ws_conn_id="telegram_presence",
        tc_box=[None],
    )
    resolved = await _resolve_inner_tick_scope_coords(
        fire_input,
        model_source=InnerTickModelSource.CHAT_DEFAULT,
    )
    assert resolved is not None
    assert resolved.chat_row_id == scope.memory_store_chat_id()
    assert resolved.chat_row_agent_id == agent_id
    await _delete_user(user.id)


@pytest.mark.asyncio
async def test_resolve_inner_tick_scope_coords_rejects_mismatched_agent_scope() -> None:
    user = await _create_guest_user()
    coordinator = Coordinator.for_loop(asyncio.get_running_loop())

    async def _noop(_text: str) -> None:
        return None

    fire_input = InnerTickFireInput(
        delivery=inner_tick_delivery_for_telegram(_noop),
        coords=InnerTickCoords(
            user_id=user.id,
            agent_id="agent-a",
            chat_id="agent-scope:wrong:pair",
        ),
        coordinator=coordinator,
        ws_conn_id="telegram_presence",
        tc_box=[None],
    )
    resolved = await _resolve_inner_tick_scope_coords(
        fire_input,
        model_source=InnerTickModelSource.CHAT_DEFAULT,
    )
    assert resolved is None
    await _delete_user(user.id)
