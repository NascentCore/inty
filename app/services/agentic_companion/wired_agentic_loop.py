"""Run agentic loop with ``ChannelTurn`` delivery and transcript-on-enqueue."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.companion_harness.loop.config import UserTurnLlmLoopMode
from app.core.companion_harness.loop.contract import AgenticLoopInput, AgenticLoopOutput
from app.core.companion_harness.loop.delivery_policy import delivery_policy_for_turn_track
from app.core.companion_harness.loop.output_queue_types import (
    OutputQueueTranscriptContext,
)
from app.core.companion_harness.loop.runner import run_agentic_loop
from app.services.agentic_companion.channel import Channel
from app.services.agentic_companion.channel_turn import ChannelTurn


@dataclass(frozen=True)
class WiredAgenticLoopRunInput:
    """Wired turn: ``AgenticLoopInput`` + ToChannel + mechanism selection."""

    loop_input: AgenticLoopInput
    llm_loop_mode: UserTurnLlmLoopMode
    channel: Channel


async def run_wired_agentic_loop(
    run: WiredAgenticLoopRunInput,
) -> AgenticLoopOutput:
    """One wired turn: ``ChannelTurn`` owns queue lifecycle and delivery."""
    loop_input = run.loop_input
    async with ChannelTurn.open(
        channel=run.channel,
        transcript_ctx=OutputQueueTranscriptContext(
            store=loop_input.store,
            transcript_rel=loop_input.transcript_rel,
            user_msg_uuid=loop_input.user_msg_uuid,
            trace_id=loop_input.trace_id,
        ),
        policy=delivery_policy_for_turn_track(
            loop_input.companion_turn_track
        ),
    ) as output_queue:
        return await run_agentic_loop(
            loop_input,
            llm_loop_mode=run.llm_loop_mode,
            output_queue=output_queue,
        )
