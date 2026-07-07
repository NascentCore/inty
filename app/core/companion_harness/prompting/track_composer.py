"""Per-track PromptPlan assembly for AgenticLoop tracks (#3463).

Generated entirely by Cursor agent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.companion_harness.companion.models import (
    ContextMeta,
    InnerTickActivity,
)
from app.core.companion_harness.companion.runtime_channel import (
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.turn_tail_user import (
    TurnTailUserMessage,
)
from app.core.companion_harness.prompt_builder import (
    PromptPlan,
    openai_dialogue_dicts_to_prompt_messages,
)
from app.core.companion_harness.prompting.bundle import PromptBundle


@dataclass(frozen=True)
class TurnComposeContext:
    """Immutable per-turn inputs for prompt composition; built by turn prep.

    Target consumer of the not-yet-wired ``compose(track, turn_ctx)`` entry that
    will drive ``select_slices_for_turn`` → ``project_slices_to_prompt_plan``.
    """

    bundle: PromptBundle
    context_meta: ContextMeta
    runtime_context: TurnRuntimeContext
    interactive_bootstrap_active: bool
    tail_user: TurnTailUserMessage
    inner_tick_activity: InnerTickActivity | None


class TrackPromptComposer:
    """Per-track PromptPlan assembly; production entry for AgenticLoop tracks.

    TODO(#3463): Add ``compose(track, turn_ctx: TurnComposeContext)`` that runs the
    ``select_slices_for_turn`` → ``project_slices_to_prompt_plan`` pipeline once the
    projection stage (#3521) renders real slices instead of delegating to legacy
    builders. Today only the OpenAI-dict interim path below is wired.
    """

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
