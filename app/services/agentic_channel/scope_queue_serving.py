"""Per-scope long-lived InputQueue drain worker and OutputQueue pump.

TODO(#3501): Hermes-style inbound quiet window after each drain before next claim;
  coalesce rapid bursts that arrive during an in-flight user turn.

Generated entirely by Cursor agent.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from loguru import logger

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.services.agentic_channel.serving import (
    SendTextFn,
    channel_output_pump,
    drain_scope_once_via_companion,
)

_SCOPE_INPUT_FALLBACK_POLL_SEC = 1.0
_SCOPE_OUTPUT_PUMP_POLL_SEC = 0.02


@dataclass(frozen=True)
class ScopeDrainCompletion:
    """One InputQueue batch completion reported from worker to presence state."""

    input_message_ids: tuple[str, ...]
    tool_background_started: bool

    def __post_init__(self) -> None:
        assert self.input_message_ids


OnDrainCompleteFn = Callable[[ScopeDrainCompletion], Awaitable[None]]


class ScopeQueueServing:
    """One AgentScope: wake-driven input drain + long-lived OutputQueue pump."""

    def __init__(
        self,
        scope: AgentScope,
        *,
        background_output_sink,
        send_text: SendTextFn,
        on_drain_complete: OnDrainCompleteFn,
    ) -> None:
        assert scope is not None
        assert send_text is not None
        assert on_drain_complete is not None
        self._scope = scope
        self._background_output_sink = background_output_sink
        self._send_text = send_text
        self._on_drain_complete = on_drain_complete
        self._wake = asyncio.Event()
        self._stop = asyncio.Event()
        self._input_task: asyncio.Task[None] | None = None
        self._pump_task: asyncio.Task[None] | None = None
        self._runtime_channel = CompanionRuntimeChannel.TELEGRAM
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

    def wake(self, *, runtime_channel: CompanionRuntimeChannel) -> None:
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

    async def _run_output_pump(self) -> None:
        try:
            await channel_output_pump(
                self._scope,
                send_text=self._send_text,
                stop_event=self._stop,
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
        while not self._stop.is_set():
            implicit_bundle = ImplicitSignalBundle(
                client_time=None,
                user_signed_on=False,
                server_received_at_utc=datetime.now(timezone.utc),
            )
            try:
                drain_result = await drain_scope_once_via_companion(
                    self._scope,
                    runtime_channel=self._runtime_channel,
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
