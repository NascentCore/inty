"""Tests for Ops Telegram idle runtime pause sweeper."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import uuid

import pytest
from sqlalchemy import delete, select

from app.core.companion_harness.agent_channel.channel_kind import (
    ChannelKind,
)
from app.db.session import AsyncSessionLocal
from app.external_services.telegram_bot_api import TelegramBotApi
from app.models.agent import Agent
from app.models.agent_channel_endpoint import AgentChannelEndpoint
from app.models.companion_bond import CompanionBond
from app.models.user import User
from app.services.agentic_channel.channel_runtime import (
    ChannelRuntimeState,
    clear_registries_for_tests,
    get_scope_channel_registry,
)
from app.services.agentic_channel.presence import (
    clear_presences_for_tests,
    get_presence,
)
from app.services.agentic_channel.provision import (
    provision_agent_for_channel_onboard,
)
from app.services.agentic_channel.endpoints import EndpointRecord
from backend.ops.telegram_demo import session_store
from backend.ops.telegram_demo.idle_sweeper import run_idle_sweeper_cycle


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


async def _age_scope(user_id: str, old_at: datetime) -> None:
    async with AsyncSessionLocal() as db:
        endpoint_row = await db.execute(
            select(AgentChannelEndpoint).where(
                AgentChannelEndpoint.user_id == user_id
            )
        )
        endpoint = endpoint_row.scalar_one()
        endpoint.created_at = old_at
        bond_row = await db.execute(
            select(CompanionBond).where(CompanionBond.user_id == user_id)
        )
        bond = bond_row.scalar_one()
        bond.created_at = old_at
        await db.commit()


@pytest.fixture(autouse=True)
async def _reset_runtime_state() -> None:
    session_store.clear_all_for_tests()
    clear_registries_for_tests()
    clear_presences_for_tests()
    yield
    session_store.clear_all_for_tests()
    clear_registries_for_tests()
    clear_presences_for_tests()


@pytest.mark.asyncio
async def test_idle_sweeper_pauses_stale_runtime() -> None:
    tag = uuid.uuid4().hex
    telegram_chat_id = f"tg-sweep-stale-{tag}"
    channel_user_id = f"tu-{tag}"
    provision = await provision_agent_for_channel_onboard(
        channel=ChannelKind.TELEGRAM,
        channel_address=telegram_chat_id,
        channel_user_id=channel_user_id,
    )
    await session_store.activate_telegram_scope(
        record=EndpointRecord(
            user_id=provision.scope.user_id,
            agent_id=provision.scope.agent_id,
            channel=ChannelKind.TELEGRAM,
            channel_address=telegram_chat_id,
            channel_user_id=channel_user_id,
        ),
        api=TelegramBotApi(bot_token="idle-sweeper-test"),
        reason="test",
    )
    assert get_presence(provision.scope) is not None
    old_at = datetime.now(UTC) - timedelta(hours=17)
    await _age_scope(provision.scope.user_id, old_at)

    await run_idle_sweeper_cycle()

    async with AsyncSessionLocal() as db:
        bond_row = await db.execute(
            select(CompanionBond).where(
                CompanionBond.user_id == provision.scope.user_id
            )
        )
        bond = bond_row.scalar_one()
        assert bond.runtime_paused_at is not None
    assert get_presence(provision.scope) is None
    registry = get_scope_channel_registry(provision.scope)
    assert (
        registry.state_of(ChannelKind.TELEGRAM) == ChannelRuntimeState.INACTIVE
    )
    await _cleanup_provision(provision.scope.user_id)


@pytest.mark.asyncio
async def test_idle_sweeper_skips_fresh_runtime() -> None:
    tag = uuid.uuid4().hex
    telegram_chat_id = f"tg-sweep-fresh-{tag}"
    channel_user_id = f"tu-{tag}"
    provision = await provision_agent_for_channel_onboard(
        channel=ChannelKind.TELEGRAM,
        channel_address=telegram_chat_id,
        channel_user_id=channel_user_id,
    )

    await run_idle_sweeper_cycle()

    async with AsyncSessionLocal() as db:
        bond_row = await db.execute(
            select(CompanionBond).where(
                CompanionBond.user_id == provision.scope.user_id
            )
        )
        bond = bond_row.scalar_one()
        assert bond.runtime_paused_at is None
    await _cleanup_provision(provision.scope.user_id)
