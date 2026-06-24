"""Tests for telegram demo session store restore."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete

from app.core.companion_harness.agent_channel.gateway import (
    GatewayKind,
)
from app.db.session import AsyncSessionLocal
from app.external_services.telegram_bot_api import TelegramBotApi
from app.models.agent import Agent
from app.models.agent_channel_endpoint import AgentChannelEndpoint
from app.models.companion_bond import CompanionBond
from app.models.user import User
from app.services.agentic_channel.channel_runtime import (
    clear_registries_for_tests,
)
from app.services.agentic_channel.companion_bonds import (
    deactivate_companion_bond,
    pause_companion_bond_runtime,
)
from app.services.agentic_channel.endpoints import EndpointRecord
from app.services.agentic_channel.errors import CompanionBondInvariantError
from app.services.agentic_channel.presence import (
    clear_presences_for_tests,
    get_presence,
)
from app.services.agentic_channel.provision import (
    provision_agent_for_channel_onboard,
)
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
        await db.execute(
            delete(CompanionBond).where(CompanionBond.user_id == user_id)
        )
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
        channel=GatewayKind.TELEGRAM,
        channel_address=telegram_chat_id,
        channel_user_id=channel_user_id,
    )
    session_store.clear_all_for_tests()
    assert (
        session_store.get_scope_for_telegram_address(telegram_chat_id) is None
    )

    api = TelegramBotApi(bot_token="restore-test")
    await session_store.restore_persisted_bindings(api=api)

    restored = session_store.get_scope_for_telegram_address(telegram_chat_id)
    assert restored is not None
    assert restored.user_id == provision.scope.user_id
    assert restored.agent_id == provision.scope.agent_id

    await _cleanup_provision(provision.scope.user_id)


@pytest.mark.asyncio
async def test_restore_skips_inactive_companion_bond() -> None:
    telegram_chat_id = f"tg-inactive-{uuid.uuid4().hex}"
    channel_user_id = f"tu-{uuid.uuid4().hex}"
    provision = await provision_agent_for_channel_onboard(
        channel=GatewayKind.TELEGRAM,
        channel_address=telegram_chat_id,
        channel_user_id=channel_user_id,
    )
    async with AsyncSessionLocal() as db:
        await deactivate_companion_bond(db, provision.scope)
        await db.commit()

    session_store.clear_all_for_tests()
    api = TelegramBotApi(bot_token="restore-inactive-test")
    await session_store.restore_persisted_bindings(api=api)

    assert (
        session_store.get_scope_for_telegram_address(telegram_chat_id) is None
    )

    await _cleanup_provision(provision.scope.user_id)


@pytest.mark.asyncio
async def test_activate_telegram_scope_rejects_inactive_bond() -> None:
    telegram_chat_id = f"tg-activate-gate-{uuid.uuid4().hex}"
    channel_user_id = f"tu-{uuid.uuid4().hex}"
    provision = await provision_agent_for_channel_onboard(
        channel=GatewayKind.TELEGRAM,
        channel_address=telegram_chat_id,
        channel_user_id=channel_user_id,
    )
    async with AsyncSessionLocal() as db:
        await deactivate_companion_bond(db, provision.scope)
        await db.commit()

    record = EndpointRecord(
        user_id=provision.scope.user_id,
        agent_id=provision.scope.agent_id,
        channel=GatewayKind.TELEGRAM,
        channel_address=telegram_chat_id,
        channel_user_id=channel_user_id,
    )
    api = TelegramBotApi(bot_token="activate-gate-test")
    with pytest.raises(CompanionBondInvariantError):
        await session_store.activate_telegram_scope(
            record=record,
            api=api,
            reason="onboard",
        )
    assert get_presence(provision.scope) is None

    await _cleanup_provision(provision.scope.user_id)


@pytest.mark.asyncio
async def test_restore_skips_paused_companion_runtime() -> None:
    telegram_chat_id = f"tg-paused-{uuid.uuid4().hex}"
    channel_user_id = f"tu-{uuid.uuid4().hex}"
    provision = await provision_agent_for_channel_onboard(
        channel=GatewayKind.TELEGRAM,
        channel_address=telegram_chat_id,
        channel_user_id=channel_user_id,
    )
    async with AsyncSessionLocal() as db:
        await pause_companion_bond_runtime(db, provision.scope)
        await db.commit()

    session_store.clear_all_for_tests()
    api = TelegramBotApi(bot_token="restore-paused-test")
    await session_store.restore_persisted_bindings(api=api)

    assert (
        session_store.get_scope_for_telegram_address(telegram_chat_id) is None
    )

    await _cleanup_provision(provision.scope.user_id)
