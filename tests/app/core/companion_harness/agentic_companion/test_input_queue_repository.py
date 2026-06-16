"""Tests for Postgres input/output queue repositories."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, select

from app.core.companion_harness.agent_channel.guest_agent_kind import (
    CompanionGuestAgentKind,
)
from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.postgres_queue import (
    PostgresInputQueueRepository,
    PostgresOutputQueueRepository,
)
from app.core.companion_harness.agentic_companion.types import (
    AgentOutputMessage,
    InboundWireMessage,
    QueueAck,
    QueueMessageId,
    QueueStatus,
)
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
from app.services.agentic_companion.downlink import DownlinkKind
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
async def test_input_queue_append_and_claim_batch_order() -> None:
    scope = await create_guest_scope_for_test(
        kind=CompanionGuestAgentKind.AGENT_CHANNEL,
        nickname_prefix="input_queue",
        meta_data={"test": True},
    )
    try:
        now = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as db:
            repo = PostgresInputQueueRepository(db)
            await repo.append_user_message(
                InboundWireMessage(
                    scope=scope,
                    channel=CompanionRuntimeChannel.TELEGRAM,
                    wire_id="wire-a",
                    text="first",
                    received_at_utc=now,
                )
            )
            await repo.append_user_message(
                InboundWireMessage(
                    scope=scope,
                    channel=CompanionRuntimeChannel.TELEGRAM,
                    wire_id="wire-a",
                    text="second",
                    received_at_utc=now,
                )
            )
            batch = await repo.claim_pending_batch(scope)
            await db.commit()
        assert batch is not None
        assert len(batch.messages) == 2
        assert [m.text for m in batch.messages] == ["first", "second"]
        assert all(m.status == QueueStatus.CLAIMED for m in batch.messages)
    finally:
        await _cleanup_scope(scope)


@pytest.mark.asyncio
async def test_mark_batch_failed_persists_after_commit() -> None:
    scope = await create_guest_scope_for_test(
        kind=CompanionGuestAgentKind.AGENT_CHANNEL,
        nickname_prefix="input_queue_failed",
        meta_data={"test": True},
    )
    try:
        now = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as db:
            repo = PostgresInputQueueRepository(db)
            await repo.append_user_message(
                InboundWireMessage(
                    scope=scope,
                    channel=CompanionRuntimeChannel.TELEGRAM,
                    wire_id="wire-a",
                    text="will fail",
                    received_at_utc=now,
                )
            )
            batch = await repo.claim_pending_batch(scope)
            assert batch is not None
            await repo.mark_batch_failed(
                batch,
                error_message="synthetic drain failure",
            )
            await db.commit()
            batch_id = batch.batch_id

        async with AsyncSessionLocal() as db:
            rows = list(
                (
                    await db.execute(
                        select(AgenticCompanionInputQueueRow).where(
                            AgenticCompanionInputQueueRow.user_id
                            == scope.user_id,
                            AgenticCompanionInputQueueRow.agent_id
                            == scope.agent_id,
                        )
                    )
                )
                .scalars()
                .all()
            )
        assert len(rows) == 1
        assert rows[0].status == QueueStatus.FAILED.value
        assert rows[0].error_message == "synthetic drain failure"
        assert rows[0].batch_id == batch_id
    finally:
        await _cleanup_scope(scope)


@pytest.mark.asyncio
async def test_output_queue_append_claim_and_deliver() -> None:
    scope = await create_guest_scope_for_test(
        kind=CompanionGuestAgentKind.AGENT_CHANNEL,
        nickname_prefix="output_queue",
        meta_data={"test": True},
    )
    try:
        async with AsyncSessionLocal() as db:
            output_repo = PostgresOutputQueueRepository(db)
            record = await output_repo.append_agent_output(
                AgentOutputMessage(
                    message_id="out-1",
                    scope=scope,
                    batch_id="batch-1",
                    kind=DownlinkKind.USER_REPLY,
                    text="hello back",
                    created_at_utc=datetime.now(timezone.utc),
                    message_ids=("in-1",),
                )
            )
            await db.commit()
        assert record.status == QueueStatus.PENDING

        async with AsyncSessionLocal() as db:
            output_repo = PostgresOutputQueueRepository(db)
            claims = await output_repo.claim_pending_for_delivery(
                scope,
                delivery_channel=CompanionRuntimeChannel.TELEGRAM,
                delivery_wire_id="wire-a",
                limit=4,
            )
            await db.commit()
        assert len(claims) == 1
        assert claims[0].record.status == QueueStatus.CLAIMED

        async with AsyncSessionLocal() as db:
            output_repo = PostgresOutputQueueRepository(db)
            await output_repo.mark_delivered(
                QueueAck(
                    message_id=QueueMessageId(value="out-1"),
                    delivered_at_utc=datetime.now(timezone.utc),
                )
            )
            await db.commit()
    finally:
        await _cleanup_scope(scope)
