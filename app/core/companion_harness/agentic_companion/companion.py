"""AgenticCompanion: per-scope serving runtime draining InputQueue into AgenticLoop.

TODO(#3493): Weixin ``drain_and_deliver`` caller should enqueue + wake only (#3487; App-WS landed in pull/3512).
"""

from __future__ import annotations

from dataclasses import dataclass

from loguru import logger

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.models import CompanionTurnResult
from app.core.companion_harness.agent_channel.channel_kind import (
    ChannelKind,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.scope_turn_lock import (
    get_scope_turn_lock,
)
from app.core.companion_harness.companion.turn_routes import (
    BackgroundToolEventSink,
)
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.utils.models_catalog import GenAIModel

from .turn import InjectedCompanionRuntime, run_agent_turn

from .output_queue import get_output_queue_for_scope
from .postgres_queue import PostgresInputQueueRepository
from .types import (
    AgenticLoopInputBatch,
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


def _agentic_loop_input_batch(
    batch: AgenticCompanionInputBatch,
) -> AgenticLoopInputBatch:
    return AgenticLoopInputBatch(
        batch_id=batch.batch_id,
        scope=batch.scope,
        messages=batch.messages,
        primary_user_msg_uuid=batch.messages[-1].message_id,
    )


@dataclass
class AgenticCompanion:
    """AgenticCompanion is the runtime of a companion, which responds to user messages and drives the autonomous activities of the agent.

    One AgentScope serving runtime: drain InputQueue, run turns, persist OutputQueue.
    """

    scope: AgentScope
    input_repo: PostgresInputQueueRepository

    async def drain_once(
        self,
        *,
        resolved_chat_model: GenAIModel,
        runtime_channel: ChannelKind,
        background_output_sink: BackgroundToolEventSink | None,
        implicit_signal_bundle: ImplicitSignalBundle,
        injected_runtime: InjectedCompanionRuntime | None = None,
    ) -> AgenticCompanionRunResult | None:
        batch = await self.input_repo.claim_pending_batch(self.scope)
        if batch is None:
            return None
        user_text = _batch_user_text(batch)
        input_batch = _agentic_loop_input_batch(batch)
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
                    injected_runtime=injected_runtime,
                    input_batch=input_batch,
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
