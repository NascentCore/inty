"""Durable outbound queue for assistant text visible to the user.

Each companion scope owns one outbound queue. Assistant replies are written to
database storage first, then held in an in-memory ready buffer for channel
delivery. Delivery workers pull ready items, send them on the active channel,
then mark rows delivered or failed for retry. This separates turn execution
(which may emit multiple partial lines during tools) from transport timing.
"""

from __future__ import annotations

import asyncio
import uuid
from threading import Lock
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
)
from app.db.session import AsyncSessionLocal
from .postgres_queue import PostgresOutputQueueRepository
from .types import (
    OutputMessageKind,
    WireAssistantSource,
    AgentOutputMessage,
    GeneratedImageRef,
    OutputQueueRecord,
    QueueAck,
    QueueMessageId,
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class OutputQueueAppendInput:
    """Payload for one user-visible assistant line.

    Carries delivery kind, visible text, optional inbound correlation, and
    observability identifiers. Foreground replies use a non-empty ``batch_id``
    and ``message_ids``; agent-initiated lines use ``batch_id=""`` and
    ``message_ids=()`` so the queue assigns a synthetic batch id.
    """

    kind: OutputMessageKind
    text: str
    batch_id: str
    message_ids: tuple[str, ...]
    trace_id: str | None
    langsmith_trace_id: str | None
    langsmith_run_id: str | None
    turn_recall: str | None
    tool_background_started: bool = False
    generated_images: tuple[GeneratedImageRef, ...] = ()
    wire_assistant_source: WireAssistantSource = WireAssistantSource.CHAT


@dataclass(frozen=True)
class ReadyOutputMessage:
    """One outbound line waiting for channel delivery.

    Produced after durable persistence succeeds; consumed by the outbound pump
    until the channel acknowledges send or reports failure.
    """

    message_id: str
    batch_id: str
    kind: OutputMessageKind
    text: str
    sequence: int
    message_ids: tuple[str, ...]
    tool_background_started: bool = False
    generated_images: tuple[GeneratedImageRef, ...] = ()
    trace_id: str | None = None
    langsmith_trace_id: str | None = None
    langsmith_run_id: str | None = None
    turn_recall: str | None = None
    wire_assistant_source: WireAssistantSource = WireAssistantSource.CHAT


_SYNTHETIC_AGENT_BATCH_PREFIX = "agent-initiated:"


def wire_assistant_source_for_record(record: OutputQueueRecord) -> WireAssistantSource:
    """Derive WS source from durable row when reloading ready messages."""
    match record.kind:
        case OutputMessageKind.TOOL_BACKGROUND:
            return WireAssistantSource.TOOL_BG
    if "implicit_sign_on_greeting" in record.batch_id:
        return WireAssistantSource.GREETING
    return WireAssistantSource.CHAT


_AGENT_INITIATED_VISIBLE_KINDS = frozenset(
    {
        OutputMessageKind.USER_REPLY,
        OutputMessageKind.PROACTIVE,
        OutputMessageKind.SCHEDULED,
        OutputMessageKind.MONOLOG,
    }
)


def ready_output_is_agent_initiated_visible(
    message: ReadyOutputMessage,
) -> bool:
    """True for agent-initiated foreground lines (empty inbound correlation)."""
    assert message is not None
    return (
        not message.message_ids
        and message.kind in _AGENT_INITIATED_VISIBLE_KINDS
    )


def ready_output_delivers_user_visible_text(
    message: ReadyOutputMessage,
) -> bool:
    """Whether adapters should push assistant text to the human on this channel.

    All known kinds deliver when their text is non-blank (monolog may be blank
    on tool-background-only turns).
    """
    match message.kind:
        case (
            OutputMessageKind.USER_REPLY
            | OutputMessageKind.PROACTIVE
            | OutputMessageKind.SCHEDULED
            | OutputMessageKind.MONOLOG
            | OutputMessageKind.TOOL_BACKGROUND
        ):
            return bool(message.text.strip())
        case _:
            return False


@dataclass(frozen=True)
class OutputDeliveryAck:
    """Confirmation that the active channel delivered one outbound line to the user."""

    message_id: str
    delivered_at_utc: datetime


@dataclass(frozen=True)
class OutputDeliveryFailure:
    """Report that channel delivery failed so the line can be retried.

    The durable row returns to a pending state and may re-enter the ready buffer.
    """

    message_id: str
    error_message: str


@dataclass(frozen=True)
class OutputDeliverySkip:
    """Report that channel delivery is impossible; row is terminal."""

    message_id: str
    error_message: str


class OutputDeliveryUnroutableError(Exception):
    """No live channel hook can deliver one ready OutputQueue row."""

    def __init__(
        self,
        scope: AgentScope,
        message_ids: tuple[str, ...],
    ) -> None:
        self.scope = scope
        self.message_ids = message_ids
        super().__init__(
            "no delivery hook for scope="
            f"{scope.registry_key()} message_ids={message_ids}"
        )


@dataclass
class OutputQueue:
    """Outbound buffer for one user–companion scope.

    Turn execution appends user-visible assistant text here; channel workers pull
    ready lines in order and track in-flight items until delivery succeeds or
    fails. One process-local instance exists per scope registry key.
    """

    scope: AgentScope
    _ready: deque[ReadyOutputMessage] = field(default_factory=deque, repr=False)
    _in_flight: dict[str, ReadyOutputMessage] = field(
        default_factory=dict, repr=False
    )
    _memory_lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    async def append_visible_message(
        self, append_input: OutputQueueAppendInput
    ) -> ReadyOutputMessage:
        """Persist one visible outbound row, then expose it for ``channel_output_pump``."""
        assert append_input.text.strip() != ""
        async with self._memory_lock:
            batch_id = append_input.batch_id
            if batch_id == "":
                batch_id = f"{_SYNTHETIC_AGENT_BATCH_PREFIX}{uuid.uuid4()}"
            message_id = str(uuid.uuid4())
            output = AgentOutputMessage(
                message_id=message_id,
                scope=self.scope,
                batch_id=batch_id,
                kind=append_input.kind,
                text=append_input.text,
                created_at_utc=_utc_now(),
                message_ids=append_input.message_ids,
                trace_id=append_input.trace_id,
                langsmith_trace_id=append_input.langsmith_trace_id,
                langsmith_run_id=append_input.langsmith_run_id,
                turn_recall=append_input.turn_recall,
                tool_background_started=append_input.tool_background_started,
                generated_images=append_input.generated_images,
            )
            async with AsyncSessionLocal() as db:
                repo = PostgresOutputQueueRepository(db)
                record = await repo.append_agent_output(output)
                await db.commit()
            ready = ReadyOutputMessage(
                message_id=record.message_id,
                batch_id=batch_id,
                kind=append_input.kind,
                text=record.text,
                sequence=record.sequence,
                message_ids=append_input.message_ids,
                tool_background_started=record.tool_background_started,
                generated_images=record.generated_images,
                trace_id=record.trace_id,
                langsmith_trace_id=record.langsmith_trace_id,
                langsmith_run_id=record.langsmith_run_id,
                turn_recall=record.turn_recall,
                wire_assistant_source=append_input.wire_assistant_source,
            )
            self._ready.append(ready)
        return ready

    def _enqueue_ready_ordered(self, message: ReadyOutputMessage) -> None:
        for index, queued in enumerate(self._ready):
            if message.sequence < queued.sequence:
                self._ready.insert(index, message)
                return
        self._ready.append(message)

    def _ready_message_from_record(
        self, record: OutputQueueRecord
    ) -> ReadyOutputMessage:
        return ReadyOutputMessage(
            message_id=record.message_id,
            batch_id=record.batch_id,
            kind=record.kind,
            text=record.text,
            sequence=record.sequence,
            message_ids=record.message_ids,
            tool_background_started=record.tool_background_started,
            generated_images=record.generated_images,
            trace_id=record.trace_id,
            langsmith_trace_id=record.langsmith_trace_id,
            langsmith_run_id=record.langsmith_run_id,
            turn_recall=record.turn_recall,
            wire_assistant_source=wire_assistant_source_for_record(record),
        )

    async def _claim_pending_from_repository(
        self,
        *,
        delivery_channel: ChannelKind,
        delivery_wire_id: str,
    ) -> tuple[ReadyOutputMessage, ...]:
        async with AsyncSessionLocal() as db:
            repo = PostgresOutputQueueRepository(db)
            claims = await repo.claim_pending_for_delivery(
                self.scope,
                delivery_channel=delivery_channel,
                delivery_wire_id=delivery_wire_id,
                limit=100,
            )
            await db.commit()
        return tuple(
            self._ready_message_from_record(claim.record) for claim in claims
        )

    async def pull_ready_batch(
        self,
        *,
        delivery_channel: ChannelKind | None = None,
        delivery_wire_id: str | None = None,
    ) -> tuple[ReadyOutputMessage, ...]:
        """Return ready messages in order and hold them in-flight until ack/failed."""
        async with self._memory_lock:
            if not self._ready:
                should_claim_persisted = (
                    delivery_channel is not None
                    and delivery_wire_id is not None
                    and delivery_wire_id != ""
                )
                if not should_claim_persisted:
                    return ()
                claimed = await self._claim_pending_from_repository(
                    delivery_channel=delivery_channel,
                    delivery_wire_id=delivery_wire_id,
                )
                for message in claimed:
                    self._enqueue_ready_ordered(message)
                if not self._ready:
                    return ()
            batch = tuple(self._ready)
            self._ready.clear()
            for message in batch:
                self._in_flight[message.message_id] = message
            return batch

    async def ack_delivered(self, ack: OutputDeliveryAck) -> None:
        """Mark one output row delivered after Channel-native send succeeded."""
        assert ack.message_id != ""
        async with AsyncSessionLocal() as db:
            repo = PostgresOutputQueueRepository(db)
            await repo.mark_delivered(
                QueueAck(
                    message_id=QueueMessageId(value=ack.message_id),
                    delivered_at_utc=ack.delivered_at_utc,
                )
            )
            await db.commit()
        async with self._memory_lock:
            self._in_flight.pop(ack.message_id, None)

    async def mark_delivery_failed(
        self, failure: OutputDeliveryFailure
    ) -> None:
        """Mark delivery failed; durable row returns to pending for retry."""
        assert failure.message_id != ""
        assert failure.error_message.strip() != ""
        async with AsyncSessionLocal() as db:
            repo = PostgresOutputQueueRepository(db)
            await repo.mark_failed(
                failure.message_id,
                error_message=failure.error_message,
            )
            await db.commit()
        async with self._memory_lock:
            self._in_flight.pop(failure.message_id, None)

    async def skip_delivery(self, skip: OutputDeliverySkip) -> None:
        """Mark delivery skipped; durable row is terminal and not requeued."""
        assert skip.message_id != ""
        assert skip.error_message.strip() != ""
        async with AsyncSessionLocal() as db:
            repo = PostgresOutputQueueRepository(db)
            await repo.mark_skipped(
                skip.message_id,
                error_message=skip.error_message,
            )
            await db.commit()
        async with self._memory_lock:
            self._in_flight.pop(skip.message_id, None)


_registries: dict[str, OutputQueue] = {}
_registry_lock = Lock()


def get_output_queue_for_scope(scope: AgentScope) -> OutputQueue:
    """Return the process-local ``OutputQueue`` for ``scope``."""
    key = scope.registry_key()
    with _registry_lock:
        existing = _registries.get(key)
        if existing is not None:
            return existing
        registry = OutputQueue(scope=scope)
        _registries[key] = registry
        return registry


def clear_output_queues_for_tests() -> None:
    """Drop all in-memory OutputQueue registries (tests only)."""
    with _registry_lock:
        _registries.clear()
