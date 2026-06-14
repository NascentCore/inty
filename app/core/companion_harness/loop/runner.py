"""Single entry: run agentic loop with config-selected mechanism."""

from __future__ import annotations

from .channel_adapter import LoopChannelAdapter
from .config import UserTurnLlmLoopMode, resolve_agentic_loop
from .contract import (
    AgenticLoopInput,
    AgenticLoopOutput,
    agentic_loop_run_bundle,
)
from .output_queue import AgenticLoopOutputQueue
from .projection import LoopProjectionContext


async def run_agentic_loop(
    loop_input: AgenticLoopInput,
    *,
    llm_loop_mode: UserTurnLlmLoopMode,
    channel: LoopChannelAdapter,
    projection: LoopProjectionContext | None = None,
) -> AgenticLoopOutput:
    """Run one interchangeable agentic loop; per-call-streaming via ``channel``."""
    mechanism = resolve_agentic_loop(llm_loop_mode)
    output_queue = AgenticLoopOutputQueue(channel=channel, projection=projection)
    bundle = agentic_loop_run_bundle(loop_input, output_queue)
    return await mechanism.run(bundle)
