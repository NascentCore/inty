"""AgenticLoop execution class and durable output queue adapter."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.loop.config import (
    UserTurnLlmLoopMode,
    resolve_agentic_loop,
)
from app.core.companion_harness.loop.contract import (
    AgenticLoopInput,
    AgenticLoopOutput,
    AgenticLoopRunBundle,
)
from app.core.companion_harness.loop.output_queue import (
    AgenticLoopOutputQueue,
    LoopDeliverable,
)
from app.core.companion_harness.loop.projection import project_deliverable
from app.core.companion_harness.agentic_companion.postgres_queue import (
    PostgresOutputQueueRepository,
)
from app.core.companion_harness.agentic_companion.repositories import (
    TranscriptProjector,
)
from app.core.companion_harness.agentic_companion.types import (
    AgentOutputMessage,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DurableAgenticLoopOutputQueue(AgenticLoopOutputQueue):
    """Persist loop emissions to durable OutputQueue via repository."""

    def __init__(
        self,
        *,
        output_repo: PostgresOutputQueueRepository,
        batch_id: str,
        scope_user_id: str,
        scope_agent_id: str,
        in_reply_to_input_ids: tuple[str, ...],
        transcript_projector: TranscriptProjector,
        store,
    ) -> None:
        assert batch_id != ""
        assert scope_user_id != ""
        assert scope_agent_id != ""
        self._output_repo = output_repo
        self._batch_id = batch_id
        self._scope_user_id = scope_user_id
        self._scope_agent_id = scope_agent_id
        self._in_reply_to_input_ids = in_reply_to_input_ids
        self._transcript_projector = transcript_projector
        self._store = store
        self._mirror: list[LoopDeliverable] = []
        self._persisted_ids: list[str] = []

    @property
    def deliverables(self) -> tuple[LoopDeliverable, ...]:
        return tuple(self._mirror)

    @property
    def persisted_message_ids(self) -> tuple[str, ...]:
        return tuple(self._persisted_ids)

    async def _push(self, deliverable: LoopDeliverable) -> None:
        self._mirror.append(deliverable)
        downlink = project_deliverable(deliverable)
        message_id = str(uuid.uuid4())
        output = AgentOutputMessage(
            message_id=message_id,
            scope=AgentScope(
                user_id=self._scope_user_id,
                agent_id=self._scope_agent_id,
            ),
            batch_id=self._batch_id,
            kind=downlink.kind,
            text=downlink.assistant_text,
            created_at_utc=_utc_now(),
            in_reply_to_input_ids=self._in_reply_to_input_ids,
            trace_id=None,
            langsmith_trace_id=None,
            langsmith_run_id=None,
            turn_recall=deliverable.turn_recall,
        )
        await self._output_repo.append_agent_output(output)
        await self._transcript_projector.project_output(
            store=self._store,
            record=output,
        )
        self._persisted_ids.append(message_id)


class AgenticLoop:
    """Run one tool-call agentic loop via interchangeable mechanism."""

    async def run(
        self,
        *,
        loop_input: AgenticLoopInput,
        llm_loop_mode: UserTurnLlmLoopMode,
        output_queue: DurableAgenticLoopOutputQueue,
    ) -> AgenticLoopOutput:
        mechanism = resolve_agentic_loop(llm_loop_mode)
        bundle = AgenticLoopRunBundle(
            loop_input=loop_input,
            output_queue=output_queue,
        )
        return await mechanism.run(bundle)
