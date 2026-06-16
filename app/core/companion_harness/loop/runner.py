"""Legacy channel-runner entry with config-selected mechanism.

TODO(#3460): Delete this sidecar runner when AgenticLoop direct user-turn
methods become the only loop execution API.
"""

from __future__ import annotations

from .channel_adapter import LoopChannelAdapter
from .config import UserTurnLlmLoopMode, resolve_agentic_loop
from .contract import (
    AgenticLoopOutput,
    LegacyAgenticLoopContext,
    agentic_loop_run_bundle,
)
from .output_queue import AgenticLoopOutputQueue


async def run_agentic_loop(
    loop_context: LegacyAgenticLoopContext,
    *,
    llm_loop_mode: UserTurnLlmLoopMode,
    channel: LoopChannelAdapter,
) -> AgenticLoopOutput:
    """Run one legacy interchangeable agentic loop; per-call-streaming via ``channel``.

    TODO(#3460): Remove after direct AgenticLoop user-turn methods replace this
    runner and the 1/2-LLM mechanism modules.
    Production ``USER_CHAT`` uses ``AgenticLoop`` direct user-turn methods with domain ``OutputQueue``.
    """
    mechanism = resolve_agentic_loop(llm_loop_mode)
    output_queue = AgenticLoopOutputQueue(channel=channel)
    bundle = agentic_loop_run_bundle(loop_context, output_queue)
    return await mechanism.run(bundle)
