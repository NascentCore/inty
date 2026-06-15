"""Repository protocols for agentic companion serving queues."""

from __future__ import annotations

from typing import Protocol

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.core.companion_harness.memory.memory_store import MemoryStore

from .types import (
    AgentOutputMessage,
    AgenticCompanionInputBatch,
    InboundWireMessage,
    OutputQueueRecord,
    QueueAck,
    QueueClaim,
    UserInputMessage,
)


class InputQueueRepository(Protocol):
    """Durable inbound user message queue."""

    async def append_user_message(
        self, inbound: InboundWireMessage
    ) -> UserInputMessage:
        """Append one pending user message."""

    async def claim_pending_batch(
        self, scope: AgentScope
    ) -> AgenticCompanionInputBatch | None:
        """Atomically claim all pending rows for ``scope``."""

    async def mark_batch_processed(
        self, batch: AgenticCompanionInputBatch
    ) -> None:
        """Mark claimed input rows processed."""

    async def mark_batch_failed(
        self,
        batch: AgenticCompanionInputBatch,
        *,
        error_message: str,
    ) -> None:
        """Mark claimed input rows failed."""


class OutputQueueRepository(Protocol):
    """Durable agent output queue (scope-neutral until delivery claim)."""

    async def append_agent_output(
        self, output: AgentOutputMessage
    ) -> OutputQueueRecord:
        """Persist one agent emission."""

    async def claim_pending_for_delivery(
        self,
        scope: AgentScope,
        *,
        delivery_channel: CompanionRuntimeChannel,
        delivery_wire_id: str,
        limit: int,
    ) -> tuple[QueueClaim, ...]:
        """Claim pending output rows for active Channel/Wire delivery."""

    async def mark_delivered(self, ack: QueueAck) -> None:
        """Mark output delivered after transport success."""

    async def mark_failed(
        self,
        message_id: str,
        *,
        error_message: str,
    ) -> None:
        """Mark delivery failed; row stays retryable."""


class TranscriptProjector(Protocol):
    """Project queue records into MemoryStore transcript.jsonl."""

    async def project_input(
        self,
        *,
        store: MemoryStore,
        record: UserInputMessage,
    ) -> None:
        """Append user transcript row for one input queue message."""

    async def project_output(
        self,
        *,
        store: MemoryStore,
        record: AgentOutputMessage,
    ) -> None:
        """Append assistant transcript row for one output queue message."""
