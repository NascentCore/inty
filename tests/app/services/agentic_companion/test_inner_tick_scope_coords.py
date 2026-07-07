"""Tests for inner-tick scope resolution (legacy chats.id vs agent-scope key)."""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import delete

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.core.companion_harness.companion.runtime_channel import ChannelKind
from app.services.agentic_companion.inner_tick_scope import (
    InnerTickFireInput,
    InnerTickModelSource,
    resolve_inner_tick_scope_coords,
)
from app.services.agentic_companion.session import Coordinator, InnerTickCoords
from tests.app.services.agentic_channel.companion_test_fixtures import (
    create_guest_user_for_test,
)


async def _create_guest_user() -> User:
    return await create_guest_user_for_test(
        nickname_prefix="inner_tick",
        meta_data={"test": True},
    )


async def _delete_user(user_id: str) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


@pytest.mark.asyncio
async def test_resolve_inner_tick_scope_coords_accepts_agent_scope_chat_id() -> (
    None
):
    user = await _create_guest_user()
    agent_id = "agent-inner-tick-test"
    scope = AgentScope(user_id=user.id, agent_id=agent_id)
    coordinator = Coordinator.for_loop(asyncio.get_running_loop())

    fire_input = InnerTickFireInput(
        runtime_channel=ChannelKind.TELEGRAM,
        coords=InnerTickCoords(
            user_id=user.id,
            agent_id=agent_id,
            chat_id=scope.memory_store_chat_id(),
        ),
        coordinator=coordinator,
        ws_conn_id="telegram_presence",
        tc_box=[None],
    )
    resolved = await resolve_inner_tick_scope_coords(
        fire_input,
        model_source=InnerTickModelSource.CHAT_DEFAULT,
    )
    assert resolved is not None
    assert resolved.chat_row_id == scope.memory_store_chat_id()
    assert resolved.chat_row_agent_id == agent_id
    await _delete_user(user.id)


@pytest.mark.asyncio
async def test_resolve_inner_tick_scope_coords_rejects_mismatched_agent_scope() -> (
    None
):
    user = await _create_guest_user()
    coordinator = Coordinator.for_loop(asyncio.get_running_loop())

    fire_input = InnerTickFireInput(
        runtime_channel=ChannelKind.TELEGRAM,
        coords=InnerTickCoords(
            user_id=user.id,
            agent_id="agent-a",
            chat_id="agent-scope:wrong:pair",
        ),
        coordinator=coordinator,
        ws_conn_id="telegram_presence",
        tc_box=[None],
    )
    resolved = await resolve_inner_tick_scope_coords(
        fire_input,
        model_source=InnerTickModelSource.CHAT_DEFAULT,
    )
    assert resolved is None
    await _delete_user(user.id)
