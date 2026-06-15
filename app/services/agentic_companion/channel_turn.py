"""Per-turn queue + delivery lifecycle at the Channel boundary."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.core.companion_harness.loop.delivery_policy import DeliveryPolicy
from app.core.companion_harness.loop.output_queue import OutputQueue
from app.core.companion_harness.loop.output_queue_types import (
    OutputQueueTranscriptContext,
)
from app.services.agentic_companion.channel import Channel
from app.services.agentic_companion.output_queue_delivery import (
    deliver_output_queue,
)


@dataclass
class ChannelTurn:
    """One user turn as seen at the Channel boundary."""

    queue: OutputQueue
    channel: Channel
    _delivery_task: asyncio.Task[None] | None = None

    @classmethod
    def open(
        cls,
        *,
        channel: Channel,
        transcript_ctx: OutputQueueTranscriptContext,
        policy: DeliveryPolicy,
    ) -> ChannelTurn:
        """Create queue and bind delivery to ``channel`` (enter context to start)."""
        queue = OutputQueue(
            transcript_ctx=transcript_ctx,
            delivery_policy=policy,
        )
        return cls(queue=queue, channel=channel)

    async def __aenter__(self) -> OutputQueue:
        self._delivery_task = asyncio.create_task(
            deliver_output_queue(self.queue, self.channel)
        )
        return self.queue

    async def __aexit__(self, *_exc: object) -> None:
        self.queue.close()
        assert self._delivery_task is not None
        await self._delivery_task
