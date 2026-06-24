"""Long-lived queue workers for one human–companion pairing scope.

Each paired user and companion agent shares one scope. While that scope is
active on a channel, this module keeps two background workers alive: one pulls
inbound user messages from durable storage and runs the companion turn, the
other continuously delivers assistant replies that were written to the outbound
queue. Inbound work is wake-driven: a new user message signals the input worker
instead of polling constantly. The output pump is the sole runtime consumer of
the outbound queue so partial replies and tool-round chatter can reach the user
before the full turn finishes.

Attach one instance per scope for the lifetime of channel presence (for example
while a Telegram session or app connection is registered). Stop both workers when
presence ends.

TODO(!3501): Hermes-style inbound quiet window after each drain before next claim;
  coalesce rapid bursts that arrive during an in-flight user turn.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from loguru import logger

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agent_channel.channel_kind import (
    ChannelKind,
)
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.services.agentic_channel.serving import (
    DeliverReadyMessageFn,
    channel_output_pump,
    drain_scope_once_via_companion,
)

_SCOPE_INPUT_FALLBACK_POLL_SEC = 1.0
_SCOPE_OUTPUT_PUMP_POLL_SEC = 0.02


@dataclass(frozen=True)
class ScopeDrainCompletion:
    """Summary emitted after one inbound batch was claimed, processed, and drained.

    Presence layer uses this to clear per-message coordination state and to
    distinguish turns that handed work to a background tool loop from turns that
    finished entirely in the foreground.
    """

    input_message_ids: tuple[str, ...]
    tool_background_started: bool

    def __post_init__(self) -> None:
        assert self.input_message_ids


OnDrainCompleteFn = Callable[[ScopeDrainCompletion], Awaitable[None]]


class ScopeQueueServing:
    """Runs inbound draining and outbound delivery for one companion scope.

    Intended use: start when channel presence comes online for a user–agent pair;
    call wake when a user message is enqueued so the input worker processes
    pending batches; stop on presence teardown. Outbound pumping starts with
    start and keeps delivering assistant text from the durable outbound queue
    until stop. The caller supplies how to send text on the active channel and
    how to record drain completion for coordination with foreground pending state.
    """

    def __init__(
        self,
        scope: AgentScope,
        *,
        background_output_sink,
        deliver_message: DeliverReadyMessageFn,
        on_drain_complete: OnDrainCompleteFn,
        runtime_channel: ChannelKind,
    ) -> None:
        assert scope is not None
        assert deliver_message is not None
        assert on_drain_complete is not None
        assert runtime_channel is not None
        self._scope = scope
        self._background_output_sink = background_output_sink
        self._deliver_message = deliver_message
        self._on_drain_complete = on_drain_complete
        self._wake = asyncio.Event()
        self._stop = asyncio.Event()
        self._input_task: asyncio.Task[None] | None = None
        self._pump_task: asyncio.Task[None] | None = None
        self._runtime_channel = runtime_channel
        self._started = False

    async def start(self) -> None:
        input_running = (
            self._input_task is not None and not self._input_task.done()
        )
        pump_running = (
            self._pump_task is not None and not self._pump_task.done()
        )
        if input_running and pump_running:
            return
        if self._started:
            await self.stop()
        self._started = True
        self._stop.clear()
        self._pump_task = asyncio.create_task(
            self._run_output_pump(),
            name=f"scope_output_pump_{self._scope.registry_key()}",
        )
        self._input_task = asyncio.create_task(
            self._run_input_worker(),
            name=f"scope_input_worker_{self._scope.registry_key()}",
        )

    def wake(self, *, runtime_channel: ChannelKind) -> None:
        assert runtime_channel is not None
        self._runtime_channel = runtime_channel
        self._wake.set()

    async def stop(self) -> None:
        if not self._started:
            return
        self._stop.set()
        self._wake.set()
        for task in (self._input_task, self._pump_task):
            if task is not None and (not task.done()):
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
        self._input_task = None
        self._pump_task = None
        self._started = False

    def _resolve_output_delivery_target(
        self,
    ) -> tuple[ChannelKind | None, str | None]:
        delivery_channel = self._runtime_channel
        if delivery_channel is None:
            return None, None
        return (
            delivery_channel,
            f"{delivery_channel.value}:{self._scope.registry_key()}",
        )

    async def _run_output_pump(self) -> None:
        try:
            await channel_output_pump(
                self._scope,
                deliver_message=self._deliver_message,
                stop_event=self._stop,
                resolve_delivery_target=self._resolve_output_delivery_target,
                poll_interval_sec=_SCOPE_OUTPUT_PUMP_POLL_SEC,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "scope_output_pump failed scope={}",
                self._scope.registry_key(),
            )

    async def _run_input_worker(self) -> None:
        while not self._stop.is_set():
            self._wake.clear()
            await self._drain_pending_batches()
            if self._stop.is_set():
                break
            try:
                await asyncio.wait_for(
                    self._wake.wait(),
                    timeout=_SCOPE_INPUT_FALLBACK_POLL_SEC,
                )
            except asyncio.TimeoutError:
                continue

    async def _drain_pending_batches(self) -> None:
        # TODO(#3567): skip drain when token budget paused; pair with stop() on exhaustion.
        runtime_channel = self._runtime_channel
        if runtime_channel is None:
            return
        while not self._stop.is_set():
            implicit_bundle = ImplicitSignalBundle(
                client_time=None,
                user_signed_on=False,
                server_received_at_utc=datetime.now(timezone.utc),
            )
            try:
                drain_result = await drain_scope_once_via_companion(
                    self._scope,
                    runtime_channel=runtime_channel,
                    implicit_signal_bundle=implicit_bundle,
                    background_output_sink=self._background_output_sink,
                )
            except Exception:
                logger.exception(
                    "scope_input_worker drain failed scope={}",
                    self._scope.registry_key(),
                )
                break
            if not drain_result.batch_drained:
                break
            if drain_result.input_message_ids:
                await self._on_drain_complete(
                    ScopeDrainCompletion(
                        input_message_ids=drain_result.input_message_ids,
                        tool_background_started=drain_result.tool_background_started,
                    )
                )
