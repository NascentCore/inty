"""Per-track PromptPlan assembly for AgenticLoop tracks (#3801)."""

from __future__ import annotations

from typing import Any

from app.core.companion_harness.companion.models import CompanionTurnTrack
from app.core.companion_harness.prompt_builder import (
    PromptBuilder,
    PromptPlan,
    openai_dialogue_dicts_to_prompt_messages,
)
from app.core.companion_harness.prompting.compose_context import TurnComposeContext


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
                return builder.scheduled_system_dicts(turn_ctx.store)
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
