"""AgenticCompanion: per-scope serving runtime draining InputQueue into AgenticLoop.

TODO(#3486): Prefer ``ScopeQueueServing`` worker loop over ad-hoc ``start_worker`` callers.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from loguru import logger

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.models import CompanionTurnResult
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.scope_turn_lock import (
    get_scope_turn_lock,
)
from app.core.companion_harness.companion.turn_routes import (
    BackgroundToolEventSink,
)
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.services.agentic_channel.turn import run_agent_turn
from app.utils.models_catalog import GenAIModel

from .output_queue import get_output_queue_for_scope
from .postgres_queue import PostgresInputQueueRepository
from .types import (
    AgenticCompanionInputBatch,
    AgenticCompanionRunResult,
    UserMessageBatch,
)


def _batch_user_text(batch: AgenticCompanionInputBatch) -> str:
    parts = [msg.text for msg in batch.messages]
    assert parts
    if len(parts) == 1:
        return parts[0]
    return "\n".join(parts)


def _batch_input_ids(batch: AgenticCompanionInputBatch) -> tuple[str, ...]:
    return tuple(msg.message_id for msg in batch.messages)


@dataclass
class AgenticCompanion:
    """AgenticCompanion is the runtime of a companion, which responds to user messages and drives the autonomous activities of the agent.

    One AgentScope serving runtime: drain InputQueue, run turns, persist OutputQueue.
    """

    scope: AgentScope
    input_repo: PostgresInputQueueRepository
    _worker_task: asyncio.Task[None] | None = field(default=None, repr=False)
    _stop: asyncio.Event = field(default_factory=asyncio.Event, repr=False)

    async def drain_once(
        self,
        *,
        resolved_chat_model: GenAIModel,
        runtime_channel: CompanionRuntimeChannel,
        background_output_sink: BackgroundToolEventSink | None,
        implicit_signal_bundle: ImplicitSignalBundle,
    ) -> AgenticCompanionRunResult | None:
        batch = await self.input_repo.claim_pending_batch(self.scope)
        if batch is None:
            return None
        user_text = _batch_user_text(batch)
        preset_uid = batch.messages[-1].message_id
        in_reply_ids = _batch_input_ids(batch)
        domain_output_queue = get_output_queue_for_scope(self.scope)
        user_message_batch = UserMessageBatch(
            batch_id=batch.batch_id,
            message_ids=in_reply_ids,
        )
        try:
            scope_lock = get_scope_turn_lock(
                CompanionScope(
                    user_id=self.scope.user_id,
                    companion_id=self.scope.agent_id,
                    chat_id=self.scope.memory_store_chat_id(),
                )
            )
            async with scope_lock:
                turn = await run_agent_turn(
                    scope=self.scope,
                    user_text=user_text,
                    resolved_chat_model=resolved_chat_model,
                    runtime_channel=runtime_channel,
                    background_output_sink=background_output_sink,
                    preset_user_msg_uuid=preset_uid,
                    implicit_signal_bundle=implicit_signal_bundle,
                    agentic_output_queue=domain_output_queue,
                    user_message_batch=user_message_batch,
                )
            assert isinstance(turn, CompanionTurnResult)
            output_ids = list(turn.output_message_ids)
            await self.input_repo.mark_batch_processed(batch)
            return AgenticCompanionRunResult(
                batch_id=batch.batch_id,
                assistant_text=turn.assistant_text,
                tool_background_started=turn.tool_background_started,
                output_message_ids=tuple(output_ids),
                input_message_ids=_batch_input_ids(batch),
            )
        except Exception as exc:
            logger.exception(
                "agentic_companion drain failed scope={}",
                self.scope.registry_key(),
            )
            await self.input_repo.mark_batch_failed(
                batch,
                error_message=repr(exc),
            )
            raise

    async def start_worker(
        self,
        *,
        poll_seconds: float,
        resolved_chat_model: GenAIModel,
        runtime_channel: CompanionRuntimeChannel,
        background_output_sink: BackgroundToolEventSink | None,
        implicit_signal_bundle: ImplicitSignalBundle,
    ) -> None:
        assert poll_seconds > 0.0
        if self._worker_task is not None and (not self._worker_task.done()):
            return
        self._stop.clear()

        async def _loop() -> None:
            while not self._stop.is_set():
                try:
                    await self.drain_once(
                        resolved_chat_model=resolved_chat_model,
                        runtime_channel=runtime_channel,
                        background_output_sink=background_output_sink,
                        implicit_signal_bundle=implicit_signal_bundle,
                    )
                except Exception:
                    logger.exception(
                        "agentic_companion worker drain_once failed scope={}",
                        self.scope.registry_key(),
                    )
                try:
                    await asyncio.wait_for(
                        self._stop.wait(),
                        timeout=poll_seconds,
                    )
                except asyncio.TimeoutError:
                    continue

        self._worker_task = asyncio.create_task(
            _loop(),
            name=f"agentic_companion_{self.scope.registry_key()}",
        )

    async def stop_worker(self) -> None:
        self._stop.set()
        task = self._worker_task
        if task is not None and (not task.done()):
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        self._worker_task = None
