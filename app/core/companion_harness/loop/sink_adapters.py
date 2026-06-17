"""Sync tool_background ``on_event`` → async per-call-streaming deliver.

TODO(!3460): Delete this sidecar adapter module when direct AgenticLoop
user-turn methods write only to agentic_companion OutputQueue.
"""

from __future__ import annotations

import asyncio

from app.core.companion_harness.companion.turn_routes import (
    BootstrapInterimOutput,
    BootstrapInterimOutputSink,
)
from app.core.companion_harness.tools.tool_background import ToolOutputEvent

from .output_queue import AgenticLoopOutputQueue

_DRAIN_SENTINEL: ToolOutputEvent | None = None


def make_bootstrap_interim_sink(
    output_queue: AgenticLoopOutputQueue,
) -> BootstrapInterimOutputSink:
    """Build interim sink that per-call-streams bootstrap interim deliverables."""

    async def _sink(interim: BootstrapInterimOutput) -> None:
        await output_queue.push_bootstrap_interim(interim)

    return _sink


def make_user_reply_per_call_sink(
    output_queue: AgenticLoopOutputQueue,
) -> BootstrapInterimOutputSink:
    """Build sink that per-call-streams each non-empty assistant text as ``USER_REPLY``."""

    async def _sink(interim: BootstrapInterimOutput) -> None:
        await output_queue.push_user_reply(assistant_text=interim.text)

    return _sink


class ToolBackgroundEventSink:
    """FIFO async drainer: sync ``on_event`` enqueues; drainer awaits each push."""

    def __init__(self, output_queue: AgenticLoopOutputQueue) -> None:
        self._output_queue = output_queue
        self._pending: asyncio.Queue[ToolOutputEvent | None] = asyncio.Queue()
        self._drainer: asyncio.Task[None] | None = None

    def __call__(self, event: ToolOutputEvent) -> None:
        if not event.output_to_user:
            return
        if not event.text.strip():
            return
        self._ensure_drainer()
        self._pending.put_nowait(event)

    def _ensure_drainer(self) -> None:
        if self._drainer is None:
            self._drainer = asyncio.create_task(self._drain())

    async def _drain(self) -> None:
        while True:
            event = await self._pending.get()
            if event is None:
                return
            await self._output_queue.push_tool_background(event)

    async def flush(self) -> None:
        """Await FIFO delivery of all events scheduled from ``on_event``."""
        if self._drainer is None:
            return
        self._pending.put_nowait(_DRAIN_SENTINEL)
        await self._drainer
        self._drainer = None
