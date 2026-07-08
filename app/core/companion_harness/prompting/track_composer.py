"""Per-track PromptPlan assembly for AgenticLoop tracks (#3463).

Generated entirely by Cursor agent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    ContextMeta,
    InnerTickActivity,
)
from app.core.companion_harness.companion.runtime_channel import (
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.turn_tail_user import (
    TurnTailUserMessage,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.prompt_builder import (
    PromptBuilder,
    PromptPlan,
    openai_dialogue_dicts_to_prompt_messages,
)
from app.core.companion_harness.prompting.bundle import PromptBundle


@dataclass(frozen=True)
class TurnComposeContext:
    """Immutable per-turn inputs for prompt composition; built by turn prep."""

    bundle: PromptBundle
    context_meta: ContextMeta
    runtime_context: TurnRuntimeContext
    interactive_bootstrap_active: bool
    tail_user: TurnTailUserMessage
    inner_tick_activity: InnerTickActivity | None
    # Proactive LIFE_CURRENTS reads; greeting/scheduled pass the same store for a uniform ctor.
    store: MemoryStore


class TrackPromptComposer:
    """Per-track prompt assembly; routes chat-only tracks to ``PromptBuilder``."""

    def system_dicts_for_track(
        self,
        track: CompanionTurnTrack,
        turn_ctx: TurnComposeContext,
    ) -> list[dict[str, Any]]:
        """System prefix only; ``turn_pipeline`` appends transcript and tail user."""
        builder = PromptBuilder(
            bundle=turn_ctx.bundle,
            context=turn_ctx.context_meta,
            runtime_context=turn_ctx.runtime_context,
        )
        match track:
            case CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING:
                return builder.greeting_system_dicts()
            case CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT:
                return builder.proactive_system_dicts(turn_ctx.store)
            case CompanionTurnTrack.INNER_TICK_SCHEDULED:
                return builder.scheduled_system_dicts()
            case _ as unexpected:
                raise AssertionError(
                    f"TrackPromptComposer.system_dicts_for_track unsupported "
                    f"track={unexpected!r}"
                )

    def compose_from_openai_messages(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: tuple[dict[str, Any], ...],
    ) -> PromptPlan:
        """Wrap pre-built OpenAI dict stacks (greeting / inner-tick interim)."""
        return PromptPlan(
            messages=openai_dialogue_dicts_to_prompt_messages(messages),
            tools=tools,
            tool_choice=None if not tools else "auto",
        )
