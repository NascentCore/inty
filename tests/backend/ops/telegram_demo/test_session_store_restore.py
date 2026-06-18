"""Tests for telegram demo session store restore."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete

from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.db.session import AsyncSessionLocal
from app.external_services.telegram_bot_api import TelegramBotApi
from app.models.agent import Agent
from app.models.agent_channel_endpoint import AgentChannelEndpoint
from app.models.companion_bond import CompanionBond
from app.models.user import User
from app.services.agentic_channel.channel_runtime import clear_registries_for_tests
from app.services.agentic_channel.presence import clear_presences_for_tests
from app.services.agentic_channel.provision import provision_agent_for_channel_onboard
from backend.ops.telegram_demo import session_store


class _NoopApi:
    pass


async def _cleanup_provision(user_id: str) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(
            delete(AgentChannelEndpoint).where(
                AgentChannelEndpoint.user_id == user_id
            )
        )
        await db.execute(delete(CompanionBond).where(CompanionBond.user_id == user_id))
        await db.execute(delete(Agent).where(Agent.creator_id == user_id))
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


@pytest.fixture(autouse=True)
async def _reset_store() -> None:
    session_store.clear_all_for_tests()
    clear_registries_for_tests()
    clear_presences_for_tests()
    yield
    session_store.clear_all_for_tests()
    clear_registries_for_tests()
    clear_presences_for_tests()


@pytest.mark.asyncio
async def test_restore_loads_endpoints_into_memory() -> None:
    telegram_chat_id = f"tg-restore-{uuid.uuid4().hex}"
    channel_user_id = f"tu-{uuid.uuid4().hex}"
    provision = await provision_agent_for_channel_onboard(
        channel=CompanionRuntimeChannel.TELEGRAM,
        channel_address=telegram_chat_id,
        channel_user_id=channel_user_id,
    )
    session_store.clear_all_for_tests()
    assert session_store.get_scope_for_telegram_address(telegram_chat_id) is None

    api = TelegramBotApi(bot_token="restore-test")
    await session_store.restore_persisted_bindings(api=api)

    restored = session_store.get_scope_for_telegram_address(telegram_chat_id)
    assert restored is not None
    assert restored.user_id == provision.scope.user_id
    assert restored.agent_id == provision.scope.agent_id

    await _cleanup_provision(provision.scope.user_id)
