"""Agentic loop runner: mechanism selection without wire/delivery concerns."""

from __future__ import annotations

from .config import UserTurnLlmLoopMode, resolve_agentic_loop
from .contract import (
    AgenticLoopInput,
    AgenticLoopOutput,
    agentic_loop_run_bundle,
)
from .output_queue import OutputQueue


class AgenticLoop:
    """Encapsulates 1-LLM / 2-LLM mechanism; output only via ``OutputQueue``."""

    def __init__(self, llm_loop_mode: UserTurnLlmLoopMode) -> None:
        self._mechanism = resolve_agentic_loop(llm_loop_mode)

    async def run(
        self,
        loop_input: AgenticLoopInput,
        output_queue: OutputQueue,
    ) -> AgenticLoopOutput:
        """Run one interchangeable agentic loop; deliverables enqueued only."""
        bundle = agentic_loop_run_bundle(loop_input, output_queue)
        return await self._mechanism.run(bundle)


async def run_agentic_loop(
    loop_input: AgenticLoopInput,
    *,
    llm_loop_mode: UserTurnLlmLoopMode,
    output_queue: OutputQueue,
) -> AgenticLoopOutput:
    """Transition wrapper around ``AgenticLoop.run``."""
    return await AgenticLoop(llm_loop_mode).run(loop_input, output_queue)
