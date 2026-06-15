"""Agentic loop outbound FIFO: enqueue writes transcript; delivery is pull-side."""

from __future__ import annotations

import asyncio
from typing import Any, Final

from app.core.companion_harness.companion.turn_routes import BootstrapInterimOutput
from app.core.companion_harness.tools.tool_background import ToolOutputEvent

from .deliverable_transcript import persist_deliverable_transcript
from .delivery_policy import DeliveryPolicy
from .loop_deliverable import LoopDeliverable, LoopDeliverableKind
from .output_queue_types import OutputQueueTranscriptContext


class QueueClosedSentinel:
    """Returned by ``pull`` after ``close``; not a deliverable."""


QUEUE_CLOSED: Final = QueueClosedSentinel()


class OutputQueue:
    """Loop outbound FIFO: enqueue mirrors + transcript; ``ChannelTurn`` drains."""

    def __init__(
        self,
        *,
        transcript_ctx: OutputQueueTranscriptContext,
        delivery_policy: DeliveryPolicy,
    ) -> None:
        self._transcript_ctx = transcript_ctx
        self._delivery_policy = delivery_policy
        self._mirror: list[LoopDeliverable] = []
        self._queue: asyncio.Queue[LoopDeliverable | QueueClosedSentinel] = (
            asyncio.Queue()
        )
        self._held_terminal: list[LoopDeliverable] = []
        self._closed = False

    @property
    def delivery_policy(self) -> DeliveryPolicy:
        return self._delivery_policy

    @property
    def deliverables(self) -> tuple[LoopDeliverable, ...]:
        """Audit mirror of everything enqueued."""
        return tuple(self._mirror)

    async def push_interim_reply(
        self, interim: BootstrapInterimOutput
    ) -> None:
        """Push one in-turn interim round (bootstrap sync tool loop)."""
        deliverable = LoopDeliverable(
            kind=LoopDeliverableKind.INTERIM_REPLY,
            assistant_text=interim.text,
            bootstrap_interim=interim,
            tool_output=None,
            significance_meta=None,
            turn_recall=None,
        )
        await self._enqueue(deliverable)

    async def push_bootstrap_interim(
        self, interim: BootstrapInterimOutput
    ) -> None:
        """Alias for ``push_interim_reply`` (legacy call sites)."""
        await self.push_interim_reply(interim)

    async def push_foreground_text(
        self,
        *,
        assistant_text: str,
        significance_meta: dict[str, Any] | None,
        turn_recall: str | None,
    ) -> None:
        """Push dual-LLM foreground envelope visible text (one LLM call)."""
        assert assistant_text.strip()
        deliverable = LoopDeliverable(
            kind=LoopDeliverableKind.FOREGROUND_TEXT,
            assistant_text=assistant_text,
            bootstrap_interim=None,
            tool_output=None,
            significance_meta=significance_meta,
            turn_recall=turn_recall,
        )
        await self._enqueue(deliverable)

    async def push_tool_background(self, event: ToolOutputEvent) -> None:
        """Push one tool_background user-visible event."""
        deliverable = LoopDeliverable(
            kind=LoopDeliverableKind.TOOL_BACKGROUND,
            assistant_text=event.text,
            bootstrap_interim=None,
            tool_output=event,
            significance_meta=event.significance_perception,
            turn_recall=event.turn_recall,
        )
        await self._enqueue(deliverable)

    async def push_user_reply(self, *, assistant_text: str) -> None:
        """Push terminal user-visible assistant text for this turn."""
        assert assistant_text.strip()
        deliverable = LoopDeliverable(
            kind=LoopDeliverableKind.USER_REPLY,
            assistant_text=assistant_text,
            bootstrap_interim=None,
            tool_output=None,
            significance_meta=None,
            turn_recall=None,
        )
        await self._enqueue(deliverable)

    async def pull(
        self,
    ) -> LoopDeliverable | QueueClosedSentinel:
        """Block until the next deliverable or queue close sentinel."""
        return await self._queue.get()

    def close(self) -> None:
        """Signal delivery task that no further deliverables will be enqueued."""
        if self._closed:
            return
        self._closed = True
        self._queue.put_nowait(QUEUE_CLOSED)

    def hold_for_flush(self, deliverable: LoopDeliverable) -> None:
        """Buffer terminal reply until ``flush_held`` after queue close."""
        self._held_terminal.append(deliverable)

    def flush_held(self) -> tuple[LoopDeliverable, ...]:
        """Drain held terminal replies in enqueue order."""
        held = tuple(self._held_terminal)
        self._held_terminal.clear()
        return held

    async def _enqueue(self, deliverable: LoopDeliverable) -> None:
        self._mirror.append(deliverable)
        persist_deliverable_transcript(
            deliverable,
            transcript_ctx=self._transcript_ctx,
        )
        await self._queue.put(deliverable)
