"""Tests for Postgres input/output queue repositories."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, select

from app.core.companion_harness.agent_channel.gateway import GatewayKind
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
from app.core.companion_harness.agent_channel.gateway import (
    GatewayKind,
)
from app.db.session import AsyncSessionLocal
from app.models.agent import Agent
from app.models.agentic_companion_queue import (
    AgenticCompanionInputQueueRow,
    AgenticCompanionOutputQueueRow,
)
from app.models.companion_bond import CompanionBond
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
        await db.execute(
            delete(CompanionBond).where(CompanionBond.user_id == scope.user_id)
        )
        await db.execute(delete(Agent).where(Agent.creator_id == scope.user_id))
        await db.execute(delete(User).where(User.id == scope.user_id))
        await db.commit()


@pytest.mark.asyncio
async def test_input_queue_append_and_claim_batch_order() -> None:
    scope = await create_guest_scope_for_test(
        gateway=GatewayKind.APP_WS,
        nickname_prefix="input_queue",
        meta_data={"test": True},
    )
    try:
        now = datetime.now(UTC)
        async with AsyncSessionLocal() as db:
            repo = PostgresInputQueueRepository(db)
            await repo.append_user_message(
                InboundWireMessage(
                    scope=scope,
                    channel=GatewayKind.TELEGRAM,
                    wire_id="wire-a",
                    text="first",
                    received_at_utc=now,
                )
            )
            await repo.append_user_message(
                InboundWireMessage(
                    scope=scope,
                    channel=GatewayKind.TELEGRAM,
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
async def test_append_user_message_idempotent_for_client_message_id() -> None:
    scope = await create_guest_scope_for_test(
        gateway=GatewayKind.APP_WS,
        nickname_prefix="input_queue_dedup",
        meta_data={"test": True},
    )
    try:
        now = datetime.now(UTC)
        client_id = "client-msg-dedup-1"
        async with AsyncSessionLocal() as db:
            repo = PostgresInputQueueRepository(db)
            first = await repo.append_user_message(
                InboundWireMessage(
                    scope=scope,
                    channel=GatewayKind.APP_WS,
                    wire_id="app:wire-1",
                    text="hello",
                    received_at_utc=now,
                    client_message_id=client_id,
                    local_id="local-1",
                    chat_history_user_row_id=99,
                )
            )
            second = await repo.append_user_message(
                InboundWireMessage(
                    scope=scope,
                    channel=GatewayKind.APP_WS,
                    wire_id="app:wire-1",
                    text="hello resend",
                    received_at_utc=now,
                    client_message_id=client_id,
                    local_id="local-1",
                    chat_history_user_row_id=99,
                )
            )
            await db.commit()

        assert first.message_id == client_id
        assert second.message_id == client_id
        assert second.local_id == "local-1"
        assert second.chat_history_user_row_id == 99

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
        assert rows[0].id == client_id
        assert rows[0].text == "hello"
    finally:
        await _cleanup_scope(scope)


@pytest.mark.asyncio
async def test_get_records_by_ids_returns_app_ws_metadata() -> None:
    scope = await create_guest_scope_for_test(
        gateway=GatewayKind.APP_WS,
        nickname_prefix="input_queue_lookup",
        meta_data={"test": True},
    )
    try:
        now = datetime.now(UTC)
        client_id = "client-msg-lookup-1"
        async with AsyncSessionLocal() as db:
            repo = PostgresInputQueueRepository(db)
            await repo.append_user_message(
                InboundWireMessage(
                    scope=scope,
                    channel=GatewayKind.APP_WS,
                    wire_id="app:wire-2",
                    text="lookup me",
                    received_at_utc=now,
                    client_message_id=client_id,
                    local_id="local-lookup",
                    chat_history_user_row_id=42,
                )
            )
            await db.commit()

        async with AsyncSessionLocal() as db:
            repo = PostgresInputQueueRepository(db)
            records = await repo.get_records_by_ids(scope, (client_id,))

        assert len(records) == 1
        assert records[0].local_id == "local-lookup"
        assert records[0].chat_history_user_row_id == 42
    finally:
        await _cleanup_scope(scope)


@pytest.mark.asyncio
async def test_mark_batch_failed_persists_after_commit() -> None:
    scope = await create_guest_scope_for_test(
        gateway=GatewayKind.APP_WS,
        nickname_prefix="input_queue_failed",
        meta_data={"test": True},
    )
    try:
        now = datetime.now(UTC)
        async with AsyncSessionLocal() as db:
            repo = PostgresInputQueueRepository(db)
            await repo.append_user_message(
                InboundWireMessage(
                    scope=scope,
                    channel=GatewayKind.TELEGRAM,
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
        gateway=GatewayKind.APP_WS,
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
                    created_at_utc=datetime.now(UTC),
                    message_ids=("in-1",),
                )
            )
            await db.commit()
        assert record.status == QueueStatus.PENDING

        async with AsyncSessionLocal() as db:
            output_repo = PostgresOutputQueueRepository(db)
            claims = await output_repo.claim_pending_for_delivery(
                scope,
                delivery_channel=GatewayKind.TELEGRAM,
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
                    delivered_at_utc=datetime.now(UTC),
                )
            )
            await db.commit()
    finally:
        await _cleanup_scope(scope)


@pytest.mark.asyncio
async def test_output_queue_mark_skipped_persists_terminal_status() -> None:
    scope = await create_guest_scope_for_test(
        gateway=GatewayKind.APP_WS,
        nickname_prefix="output_queue_skipped",
        meta_data={"test": True},
    )
    try:
        async with AsyncSessionLocal() as db:
            output_repo = PostgresOutputQueueRepository(db)
            await output_repo.append_agent_output(
                AgentOutputMessage(
                    message_id="out-skip",
                    scope=scope,
                    batch_id="batch-1",
                    kind=DownlinkKind.USER_REPLY,
                    text="orphan reply",
                    created_at_utc=datetime.now(UTC),
                    message_ids=("in-orphan",),
                )
            )
            await output_repo.claim_pending_for_delivery(
                scope,
                delivery_channel=GatewayKind.TELEGRAM,
                delivery_wire_id="wire-a",
                limit=4,
            )
            await output_repo.mark_skipped(
                "out-skip",
                error_message="no delivery hook",
            )
            await db.commit()

        async with AsyncSessionLocal() as db:
            row = (
                await db.execute(
                    select(AgenticCompanionOutputQueueRow).where(
                        AgenticCompanionOutputQueueRow.id == "out-skip"
                    )
                )
            ).scalar_one()
        assert row.status == QueueStatus.SKIPPED.value
        assert row.error_message == "no delivery hook"
        assert row.delivery_channel is None
        assert row.delivery_wire_id is None
        assert row.claimed_at is None
    finally:
        await _cleanup_scope(scope)
