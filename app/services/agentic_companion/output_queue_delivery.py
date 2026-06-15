"""Drain ``OutputQueue`` into ``Channel.deliver`` with bootstrap terminal defer."""

from __future__ import annotations

from app.core.companion_harness.loop.output_queue import (
    QUEUE_CLOSED,
    OutputQueue,
)
from app.services.agentic_companion.channel import Channel
from app.services.agentic_companion.loop_deliverable_projection import (
    project_deliverable,
)


async def deliver_output_queue(queue: OutputQueue, channel: Channel) -> None:
    """Pull deliverables until close; honor ``queue.delivery_policy`` terminal hold."""
    while True:
        item = await queue.pull()
        if item is QUEUE_CLOSED:
            break
        if queue.delivery_policy.holds_terminal_reply(item):
            queue.hold_for_flush(item)
            continue
        await channel.deliver(project_deliverable(item))
    for held in queue.flush_held():
        await channel.deliver(project_deliverable(held))
