"""Tests for AgenticCompanion OutputQueue writes on drain_once."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import delete, select

from app.core.companion_harness.agent_channel.guest_agent_kind import (
    CompanionGuestAgentKind,
)
from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.companion import AgenticCompanion
from app.core.companion_harness.agentic_companion.postgres_queue import (
    PostgresInputQueueRepository,
    PostgresOutputQueueRepository,
)
from app.core.companion_harness.agentic_companion.types import InboundWireMessage
from app.core.companion_harness.companion.models import CompanionTurnResult
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.db.session import AsyncSessionLocal
from app.models.agent import Agent
from app.models.agentic_companion_queue import (
    AgenticCompanionInputQueueRow,
    AgenticCompanionOutputQueueRow,
)
from app.models.user import User
from app.schemas.implicit_signals import ImplicitSignalBundle
from tests.app.services.agentic_channel.companion_test_fixtures import (
    create_guest_scope_for_test,
)


async def _cleanup_scope(scope: AgentScope) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(
            delete(AgenticCompanionInputQueueRow).where(
                AgenticCompanionInputQueueRow.user_id == scope.user_id
            )
        )
        await db.execute(
            delete(AgenticCompanionOutputQueueRow).where(
                AgenticCompanionOutputQueueRow.user_id == scope.user_id
            )
        )
        await db.execute(delete(Agent).where(Agent.creator_id == scope.user_id))
        await db.execute(delete(User).where(User.id == scope.user_id))
        await db.commit()


@pytest.mark.asyncio
async def test_drain_skips_output_queue_when_tool_background_without_text() -> None:
    scope = await create_guest_scope_for_test(
        kind=CompanionGuestAgentKind.AGENT_CHANNEL,
        nickname_prefix="companion_drain_tool_bg",
        meta_data={"test": True},
    )
    try:
        async with AsyncSessionLocal() as db:
            input_repo = PostgresInputQueueRepository(db)
            await input_repo.append_user_message(
                InboundWireMessage(
                    scope=scope,
                    channel=CompanionRuntimeChannel.TELEGRAM,
                    wire_id="wire-tool-bg",
                    text="trigger tools",
                    received_at_utc=datetime.now(timezone.utc),
                )
            )
            await db.commit()

        turn_result = CompanionTurnResult(
            assistant_text="",
            tool_background_started=True,
        )
        with patch(
            "app.core.companion_harness.agentic_companion.companion.run_agent_turn",
            new_callable=AsyncMock,
            return_value=turn_result,
        ):
            async with AsyncSessionLocal() as db:
                companion = AgenticCompanion(
                    scope=scope,
                    input_repo=PostgresInputQueueRepository(db),
                    output_repo=PostgresOutputQueueRepository(db),
                )
                result = await companion.drain_once(
                    resolved_chat_model=object(),
                    runtime_channel=CompanionRuntimeChannel.TELEGRAM,
                    background_output_sink=None,
                    implicit_signal_bundle=ImplicitSignalBundle(
                        client_time=None,
                        user_signed_on=False,
                        server_received_at_utc=datetime.now(timezone.utc),
                    ),
                )
                await db.commit()

        assert result is not None
        assert result.output_message_ids == ()

        async with AsyncSessionLocal() as db:
            rows = (
                (
                    await db.execute(
                        select(AgenticCompanionOutputQueueRow).where(
                            AgenticCompanionOutputQueueRow.user_id
                            == scope.user_id,
                            AgenticCompanionOutputQueueRow.agent_id
                            == scope.agent_id,
                        )
                    )
                )
                .scalars()
                .all()
            )
        assert rows == []
    finally:
        await _cleanup_scope(scope)
