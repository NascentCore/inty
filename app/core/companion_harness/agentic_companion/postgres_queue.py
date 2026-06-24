"""Postgres-backed InputQueue and OutputQueue repositories."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agent_channel.channel_kind import (
    ChannelKind,
)
from app.models.agentic_companion_queue import (
    AgenticCompanionInputQueueRow,
    AgenticCompanionOutputQueueRow,
)
from app.services.agentic_companion.downlink import DownlinkKind

from .types import (
    AgentOutputMessage,
    AgenticCompanionInputBatch,
    GeneratedImageRef,
    InboundWireMessage,
    InputQueueRecord,
    OutputQueueRecord,
    QueueAck,
    QueueClaim,
    QueueStatus,
    UserInputMessage,
    WireId,
)

_OUTPUT_CLAIM_STALE_AFTER = timedelta(minutes=5)
_OUTPUT_RETRY_AFTER = timedelta(seconds=2)
_OUTPUT_MAX_DELIVERY_ATTEMPTS = 3


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _scope_filters(scope: AgentScope) -> tuple:
    return (
        AgenticCompanionInputQueueRow.user_id == scope.user_id,
        AgenticCompanionInputQueueRow.agent_id == scope.agent_id,
    )


def _output_scope_filters(scope: AgentScope) -> tuple:
    return (
        AgenticCompanionOutputQueueRow.user_id == scope.user_id,
        AgenticCompanionOutputQueueRow.agent_id == scope.agent_id,
    )


def _input_row_to_record(
    row: AgenticCompanionInputQueueRow,
) -> InputQueueRecord:
    return InputQueueRecord(
        message_id=row.id,
        scope=AgentScope(user_id=row.user_id, agent_id=row.agent_id),
        sequence=int(row.sequence_id),
        status=QueueStatus(row.status),
        channel=ChannelKind(row.channel),
        wire_id=row.wire_id,
        text=row.text,
        received_at_utc=row.created_at,
        client_message_id=row.client_message_id,
        local_id=row.local_id,
        chat_history_user_row_id=row.chat_history_user_row_id,
        batch_id=row.batch_id,
    )


def _generated_image_refs_from_json(
    raw: str | None,
) -> tuple[GeneratedImageRef, ...]:
    rows = json.loads(raw or "[]")
    assert isinstance(rows, list)
    return tuple(GeneratedImageRef.model_validate(row) for row in rows)


def _generated_image_refs_to_json(
    images: tuple[GeneratedImageRef, ...],
) -> str:
    return json.dumps(
        [image.model_dump(exclude_none=True) for image in images],
        ensure_ascii=False,
    )


def _output_row_to_record(
    row: AgenticCompanionOutputQueueRow,
) -> OutputQueueRecord:
    raw_ids = json.loads(row.message_ids_json or "[]")
    message_ids = tuple(str(x) for x in raw_ids)
    delivery_channel = (
        ChannelKind(row.delivery_channel) if row.delivery_channel else None
    )
    return OutputQueueRecord(
        message_id=row.id,
        scope=AgentScope(user_id=row.user_id, agent_id=row.agent_id),
        sequence=int(row.sequence_id),
        status=QueueStatus(row.status),
        batch_id=row.batch_id,
        kind=DownlinkKind(row.kind),
        text=row.text,
        created_at_utc=row.created_at,
        message_ids=message_ids,
        trace_id=row.trace_id,
        langsmith_trace_id=row.langsmith_trace_id,
        langsmith_run_id=row.langsmith_run_id,
        turn_recall=row.turn_recall,
        tool_background_started=bool(row.tool_background_started),
        generated_images=_generated_image_refs_from_json(
            row.generated_images_json
        ),
        delivery_channel=delivery_channel,
        delivery_wire_id=row.delivery_wire_id,
        delivery_attempt_count=int(row.delivery_attempt_count or 0),
    )


class PostgresInputQueueRepository:
    """SQLAlchemy async durable inbound user message queue."""

    def __init__(self, db: AsyncSession) -> None:
        assert db is not None
        self._db = db

    async def append_user_message(
        self, inbound: InboundWireMessage
    ) -> UserInputMessage:
        message_id = inbound.client_message_id or str(uuid.uuid4())
        if inbound.client_message_id is not None:
            existing = await self._db.get(
                AgenticCompanionInputQueueRow,
                inbound.client_message_id,
            )
            if existing is not None:
                return UserInputMessage(
                    message_id=existing.id,
                    scope=AgentScope(
                        user_id=existing.user_id,
                        agent_id=existing.agent_id,
                    ),
                    channel=ChannelKind(existing.channel),
                    wire_id=existing.wire_id,
                    text=existing.text,
                    received_at_utc=existing.created_at,
                    client_message_id=existing.client_message_id,
                    local_id=existing.local_id,
                    chat_history_user_row_id=existing.chat_history_user_row_id,
                )
        row = AgenticCompanionInputQueueRow(
            id=message_id,
            user_id=inbound.scope.user_id,
            agent_id=inbound.scope.agent_id,
            status=QueueStatus.PENDING.value,
            channel=inbound.channel.value,
            wire_id=inbound.wire_id,
            client_message_id=inbound.client_message_id,
            local_id=inbound.local_id,
            chat_history_user_row_id=inbound.chat_history_user_row_id,
            text=inbound.text,
        )
        self._db.add(row)
        await self._db.flush()
        await self._db.refresh(row)
        return UserInputMessage(
            message_id=message_id,
            scope=inbound.scope,
            channel=inbound.channel,
            wire_id=inbound.wire_id,
            text=inbound.text,
            received_at_utc=row.created_at,
            client_message_id=inbound.client_message_id,
            local_id=inbound.local_id,
            chat_history_user_row_id=inbound.chat_history_user_row_id,
        )

    async def get_records_by_ids(
        self,
        scope: AgentScope,
        message_ids: tuple[str, ...],
    ) -> tuple[InputQueueRecord, ...]:
        """Load durable input rows for OutputQueue downlink correlation."""
        assert message_ids
        user_filter, agent_filter = _scope_filters(scope)
        stmt = (
            select(AgenticCompanionInputQueueRow)
            .where(
                user_filter,
                agent_filter,
                AgenticCompanionInputQueueRow.id.in_(message_ids),
            )
            .order_by(AgenticCompanionInputQueueRow.sequence_id.asc())
        )
        result = await self._db.execute(stmt)
        return tuple(_input_row_to_record(row) for row in result.scalars())

    async def claim_pending_batch(
        self, scope: AgentScope
    ) -> AgenticCompanionInputBatch | None:
        user_filter, agent_filter = _scope_filters(scope)
        stmt = (
            select(AgenticCompanionInputQueueRow)
            .where(
                user_filter,
                agent_filter,
                AgenticCompanionInputQueueRow.status
                == QueueStatus.PENDING.value,
            )
            .order_by(AgenticCompanionInputQueueRow.sequence_id.asc())
            .with_for_update(skip_locked=True)
        )
        result = await self._db.execute(stmt)
        rows = list(result.scalars().all())
        if not rows:
            return None
        batch_id = str(uuid.uuid4())
        claimed_at = _utc_now()
        for row in rows:
            row.status = QueueStatus.CLAIMED.value
            row.batch_id = batch_id
            row.claimed_at = claimed_at
        await self._db.flush()
        records = tuple(_input_row_to_record(row) for row in rows)
        return AgenticCompanionInputBatch(
            batch_id=batch_id,
            scope=scope,
            messages=records,
            claimed_at_utc=claimed_at,
        )

    async def mark_batch_processed(
        self, batch: AgenticCompanionInputBatch
    ) -> None:
        processed_at = _utc_now()
        user_filter, agent_filter = _scope_filters(batch.scope)
        await self._db.execute(
            update(AgenticCompanionInputQueueRow)
            .where(
                user_filter,
                agent_filter,
                AgenticCompanionInputQueueRow.batch_id == batch.batch_id,
            )
            .values(
                status=QueueStatus.DELIVERED.value,
                processed_at=processed_at,
            )
        )

    async def mark_batch_failed(
        self,
        batch: AgenticCompanionInputBatch,
        *,
        error_message: str,
    ) -> None:
        assert error_message.strip() != ""
        failed_at = _utc_now()
        user_filter, agent_filter = _scope_filters(batch.scope)
        await self._db.execute(
            update(AgenticCompanionInputQueueRow)
            .where(
                user_filter,
                agent_filter,
                AgenticCompanionInputQueueRow.batch_id == batch.batch_id,
            )
            .values(
                status=QueueStatus.FAILED.value,
                failed_at=failed_at,
                error_message=error_message.strip(),
            )
        )


class PostgresOutputQueueRepository:
    """SQLAlchemy async durable agent output queue."""

    def __init__(self, db: AsyncSession) -> None:
        assert db is not None
        self._db = db

    async def append_agent_output(
        self, output: AgentOutputMessage
    ) -> OutputQueueRecord:
        message_id = output.message_id or str(uuid.uuid4())
        row = AgenticCompanionOutputQueueRow(
            id=message_id,
            user_id=output.scope.user_id,
            agent_id=output.scope.agent_id,
            status=QueueStatus.PENDING.value,
            batch_id=output.batch_id,
            kind=output.kind.value,
            text=output.text,
            message_ids_json=json.dumps(
                list(output.message_ids),
                ensure_ascii=False,
            ),
            trace_id=output.trace_id,
            langsmith_trace_id=output.langsmith_trace_id,
            langsmith_run_id=output.langsmith_run_id,
            turn_recall=output.turn_recall,
            tool_background_started=output.tool_background_started,
            generated_images_json=_generated_image_refs_to_json(
                output.generated_images
            ),
        )
        self._db.add(row)
        await self._db.flush()
        await self._db.refresh(row)
        return _output_row_to_record(row)

    async def claim_pending_for_delivery(
        self,
        scope: AgentScope,
        *,
        delivery_channel: ChannelKind,
        delivery_wire_id: str,
        limit: int,
    ) -> tuple[QueueClaim, ...]:
        assert delivery_wire_id != ""
        assert limit > 0
        user_filter, agent_filter = _output_scope_filters(scope)
        stale_claimed_before = _utc_now() - _OUTPUT_CLAIM_STALE_AFTER
        retry_ready_before = _utc_now() - _OUTPUT_RETRY_AFTER
        stmt = (
            select(AgenticCompanionOutputQueueRow)
            .where(
                user_filter,
                agent_filter,
                or_(
                    and_(
                        AgenticCompanionOutputQueueRow.status
                        == QueueStatus.PENDING.value,
                        or_(
                            AgenticCompanionOutputQueueRow.failed_at.is_(None),
                            AgenticCompanionOutputQueueRow.failed_at
                            <= retry_ready_before,
                        ),
                    ),
                    and_(
                        AgenticCompanionOutputQueueRow.status
                        == QueueStatus.CLAIMED.value,
                        AgenticCompanionOutputQueueRow.claimed_at
                        < stale_claimed_before,
                    ),
                ),
            )
            .order_by(AgenticCompanionOutputQueueRow.sequence_id.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self._db.execute(stmt)
        rows = list(result.scalars().all())
        if not rows:
            return ()
        claimed_at = _utc_now()
        claims: list[QueueClaim] = []
        for row in rows:
            row.status = QueueStatus.CLAIMED.value
            row.delivery_channel = delivery_channel.value
            row.delivery_wire_id = delivery_wire_id
            row.claimed_at = claimed_at
            row.delivery_attempt_count = (
                int(row.delivery_attempt_count or 0) + 1
            )
            record = _output_row_to_record(row)
            claims.append(
                QueueClaim(
                    record=record,
                    delivery_channel=delivery_channel,
                    delivery_wire_id=WireId(value=delivery_wire_id),
                )
            )
        await self._db.flush()
        return tuple(claims)

    async def mark_delivered(self, ack: QueueAck) -> None:
        delivered_at = ack.delivered_at_utc
        await self._db.execute(
            update(AgenticCompanionOutputQueueRow)
            .where(AgenticCompanionOutputQueueRow.id == ack.message_id.value)
            .values(
                status=QueueStatus.DELIVERED.value,
                delivered_at=delivered_at,
            )
        )

    async def mark_failed(
        self,
        message_id: str,
        *,
        error_message: str,
    ) -> None:
        assert message_id != ""
        assert error_message.strip() != ""
        failed_at = _utc_now()
        row = await self._db.get(AgenticCompanionOutputQueueRow, message_id)
        if row is None:
            return
        attempts = int(row.delivery_attempt_count or 0)
        status = (
            QueueStatus.SKIPPED.value
            if attempts >= _OUTPUT_MAX_DELIVERY_ATTEMPTS
            else QueueStatus.PENDING.value
        )
        await self._db.execute(
            update(AgenticCompanionOutputQueueRow)
            .where(AgenticCompanionOutputQueueRow.id == message_id)
            .values(
                status=status,
                failed_at=failed_at,
                error_message=error_message.strip(),
                delivery_channel=None,
                delivery_wire_id=None,
                claimed_at=None,
            )
        )

    async def mark_skipped(
        self,
        message_id: str,
        *,
        error_message: str,
    ) -> None:
        assert message_id != ""
        assert error_message.strip() != ""
        failed_at = _utc_now()
        await self._db.execute(
            update(AgenticCompanionOutputQueueRow)
            .where(AgenticCompanionOutputQueueRow.id == message_id)
            .values(
                status=QueueStatus.SKIPPED.value,
                failed_at=failed_at,
                error_message=error_message.strip(),
                delivery_channel=None,
                delivery_wire_id=None,
                claimed_at=None,
            )
        )
