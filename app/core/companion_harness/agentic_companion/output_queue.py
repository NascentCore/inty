"""Per-scope OutputQueue: durable append + in-memory ready delivery buffer."""

from __future__ import annotations

import asyncio
import uuid
from threading import Lock
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.db.session import AsyncSessionLocal
from app.services.agentic_companion.downlink import DownlinkKind

from .postgres_queue import PostgresOutputQueueRepository
from .types import AgentOutputMessage, QueueAck, QueueMessageId


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class OutputQueueAppendInput:
    """One user-visible assistant emission to persist and queue for delivery."""

    batch_id: str
    text: str
    message_ids: tuple[str, ...]
    trace_id: str | None
    langsmith_trace_id: str | None
    langsmith_run_id: str | None
    turn_recall: str | None


@dataclass(frozen=True)
class ReadyOutputMessage:
    """In-memory delivery marker after durable OutputQueue append succeeded."""

    message_id: str
    batch_id: str
    kind: DownlinkKind
    text: str
    sequence: int
    message_ids: tuple[str, ...]


@dataclass(frozen=True)
class OutputDeliveryAck:
    """Successful Channel delivery acknowledgement."""

    message_id: str
    delivered_at_utc: datetime


@dataclass(frozen=True)
class OutputDeliveryFailure:
    """Failed Channel delivery; row stays retryable in durable store."""

    message_id: str
    error_message: str


@dataclass
class OutputQueue:
    """Scope-neutral outbound buffer: DB persist first, then in-memory ready queue."""

    scope: AgentScope
    _ready: deque[ReadyOutputMessage] = field(default_factory=deque, repr=False)
    _in_flight: dict[str, ReadyOutputMessage] = field(
        default_factory=dict, repr=False
    )
    _memory_lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    async def append_user_reply(
        self, append_input: OutputQueueAppendInput
    ) -> ReadyOutputMessage:
        """Persist one ``USER_REPLY`` row, then expose it for ``channel_output_pump``."""
        assert append_input.batch_id != ""
        assert append_input.text.strip() != ""
        message_id = str(uuid.uuid4())
        output = AgentOutputMessage(
            message_id=message_id,
            scope=self.scope,
            batch_id=append_input.batch_id,
            kind=DownlinkKind.USER_REPLY,
            text=append_input.text,
            created_at_utc=_utc_now(),
            message_ids=append_input.message_ids,
            trace_id=append_input.trace_id,
            langsmith_trace_id=append_input.langsmith_trace_id,
            langsmith_run_id=append_input.langsmith_run_id,
            turn_recall=append_input.turn_recall,
        )
        async with AsyncSessionLocal() as db:
            repo = PostgresOutputQueueRepository(db)
            record = await repo.append_agent_output(output)
            await db.commit()
        ready = ReadyOutputMessage(
            message_id=record.message_id,
            batch_id=append_input.batch_id,
            kind=DownlinkKind.USER_REPLY,
            text=record.text,
            sequence=record.sequence,
            message_ids=append_input.message_ids,
        )
        async with self._memory_lock:
            self._ready.append(ready)
        return ready

    def _enqueue_ready_ordered(self, message: ReadyOutputMessage) -> None:
        for index, queued in enumerate(self._ready):
            if message.sequence < queued.sequence:
                self._ready.insert(index, message)
                return
        self._ready.append(message)

    async def pull_ready_batch(self) -> tuple[ReadyOutputMessage, ...]:
        """Return ready messages in order and hold them in-flight until ack/failed."""
        async with self._memory_lock:
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
            message = self._in_flight.pop(failure.message_id, None)
            if message is not None:
                self._enqueue_ready_ordered(message)


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
