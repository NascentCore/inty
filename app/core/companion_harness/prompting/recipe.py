"""Track × phase × leg recipes for production system-prefix core stack assembly.

``compose_system_prefix`` is the single source of truth for Doctrine through
Contextual ordering on the four imperative paths left after pull/3829 Phase 1.
Peripheral slices (channel output format, Weixin alias, reply-language) stay at
callers; see ``prompt_stack.append_peripheral_system_slices``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.companion_harness.companion.ai_private_prompt import (
    get_ai_private_jsonl_text_for_prompt,
)
from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    ContextMeta,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.prompting.bundle import PromptBundle
from app.core.companion_harness.prompting.compose_context import (
    TurnComposeContext,
    build_turn_compose_context,
    default_runtime_context_for_compose,
    empty_memory_store_for_compose,
    extend_contextual_system_slices,
    turn_compose_context_for_self_contained_track,
    turn_compose_context_for_user_turn_chat_leg,
    turn_compose_context_for_user_turn_tool_leg,
)
from app.core.companion_harness.prompting.leg_kind import PromptLegKind
from app.core.companion_harness.prompting.phase import Phase
from app.core.companion_harness.prompting.system_messages import (
    _auxiliary_system_messages,
    _capability_system_messages,
    _doctrine_system_messages,
    _output_system_messages,
    _persona_system_messages,
)
from app.core.companion_harness.prompting.tracks import (
    _capability_settled_dual_chat_leg_system_messages,
    _output_settled_dual_chat_leg_system_messages,
    _persona_settled_user_turn_system_messages,
)


@dataclass(frozen=True)
class TrackSystemRecipeKey:
    """Lookup key for one production system-prefix recipe (track × phase × leg)."""

    # Production turn track being composed.
    track: CompanionTurnTrack
    # Bootstrap vs settled within the track.
    phase: Phase
    # LLM request leg; dual-LLM USER_CHAT uses CHAT_LEG or TOOL_LEG.
    leg_kind: PromptLegKind


def resolve_track_system_recipe_key(ctx: TurnComposeContext) -> TrackSystemRecipeKey:
    """Derive recipe lookup key from immutable compose context."""
    return TrackSystemRecipeKey(
        track=ctx.track,
        phase=ctx.phase,
        leg_kind=ctx.leg_kind,
    )


def compose_system_prefix(ctx: TurnComposeContext) -> list[dict[str, Any]]:
    """Assemble core system prefix for one registered (track, phase, leg_kind) recipe."""
    key = resolve_track_system_recipe_key(ctx)
    match key.phase:
        case Phase.BOOTSTRAP:
            match key.leg_kind:
                case PromptLegKind.CHAT_LEG | PromptLegKind.TOOL_LEG:
                    raise NotImplementedError(
                        "TODO(#3453): dual-LLM bootstrap phase not migrated; use PromptBuilder "
                        "for single-LLM bootstrap AgenticLoop execution"
                    )
                case _:
                    pass
        case Phase.SETTLED:
            pass
    out: list[dict[str, Any]] = []
    match key:
        case TrackSystemRecipeKey(
            CompanionTurnTrack.INNER_TICK_MONOLOG,
            Phase.SETTLED,
            PromptLegKind.SINGLE_LLM,
        ):
            ai_private_text = get_ai_private_jsonl_text_for_prompt(ctx.store)
            out.extend(_doctrine_system_messages())
            out.extend(_auxiliary_system_messages())
            out.extend(
                _capability_system_messages(
                    bundle=ctx.bundle,
                    tools_on=True,
                    chat_branch_no_tool_api=False,
                    tool_side_compact=True,
                    inner_tick_turn=True,
                    interactive_bootstrap_active=False,
                )
            )
            out.extend(
                _persona_system_messages(
                    bundle=ctx.bundle,
                    context=ctx.context_meta,
                    inner_tick_turn=True,
                    skip_memory_blocks=False,
                    include_significance_perception_slice=False,
                    interactive_bootstrap_active=False,
                )
            )
            out.extend(
                _output_system_messages(
                    inner_tick_turn=True,
                    tick_proactive=False,
                    tools_on=True,
                    tool_side_compact=True,
                    async_foreground_chat_stack=False,
                    interactive_bootstrap_active=False,
                    include_significance_perception_slice=False,
                    chat_branch_no_tool_api=False,
                )
            )
            extend_contextual_system_slices(
                out,
                turn_compose_context_for_self_contained_track(
                    bundle=ctx.bundle,
                    context_meta=ctx.context_meta,
                    store=ctx.store,
                    track=CompanionTurnTrack.INNER_TICK_MONOLOG,
                    ai_private_text=ai_private_text,
                    proactive_life_currents_block=None,
                ),
            )
        case TrackSystemRecipeKey(
            CompanionTurnTrack.INNER_TICK_AUTONOMY,
            Phase.SETTLED,
            PromptLegKind.SINGLE_LLM,
        ):
            out.extend(_doctrine_system_messages())
            out.extend(
                _capability_system_messages(
                    bundle=ctx.bundle,
                    tools_on=True,
                    chat_branch_no_tool_api=False,
                    tool_side_compact=True,
                    inner_tick_turn=True,
                    interactive_bootstrap_active=False,
                )
            )
            out.extend(
                _persona_system_messages(
                    bundle=ctx.bundle,
                    context=ctx.context_meta,
                    inner_tick_turn=True,
                    skip_memory_blocks=False,
                    include_significance_perception_slice=False,
                    interactive_bootstrap_active=False,
                )
            )
            out.extend(
                _output_system_messages(
                    inner_tick_turn=True,
                    tick_proactive=False,
                    tools_on=True,
                    tool_side_compact=True,
                    async_foreground_chat_stack=False,
                    interactive_bootstrap_active=False,
                    include_significance_perception_slice=False,
                    chat_branch_no_tool_api=False,
                )
            )
            extend_contextual_system_slices(
                out,
                turn_compose_context_for_self_contained_track(
                    bundle=ctx.bundle,
                    context_meta=ctx.context_meta,
                    store=ctx.store,
                    track=CompanionTurnTrack.INNER_TICK_AUTONOMY,
                    ai_private_text="",
                    proactive_life_currents_block=None,
                ),
            )
        case TrackSystemRecipeKey(
            CompanionTurnTrack.USER_CHAT,
            Phase.SETTLED,
            PromptLegKind.CHAT_LEG,
        ):
            out.extend(_doctrine_system_messages())
            out.extend(_auxiliary_system_messages())
            out.extend(_capability_settled_dual_chat_leg_system_messages())
            out.extend(
                _persona_settled_user_turn_system_messages(
                    bundle=ctx.bundle,
                    context=ctx.context_meta,
                    include_significance_perception_slice=True,
                )
            )
            out.extend(_output_settled_dual_chat_leg_system_messages())
            extend_contextual_system_slices(
                out,
                turn_compose_context_for_user_turn_chat_leg(
                    bundle=ctx.bundle,
                    context_meta=ctx.context_meta,
                    phase=Phase.SETTLED,
                ),
            )
        case TrackSystemRecipeKey(
            CompanionTurnTrack.USER_CHAT,
            Phase.SETTLED,
            PromptLegKind.TOOL_LEG,
        ):
            out.extend(_doctrine_system_messages())
            out.extend(_auxiliary_system_messages())
            out.extend(
                _capability_system_messages(
                    bundle=ctx.bundle,
                    tools_on=True,
                    chat_branch_no_tool_api=False,
                    tool_side_compact=True,
                    inner_tick_turn=False,
                    interactive_bootstrap_active=False,
                )
            )
            out.extend(
                _persona_system_messages(
                    bundle=ctx.bundle,
                    context=ctx.context_meta,
                    inner_tick_turn=False,
                    skip_memory_blocks=True,
                    include_significance_perception_slice=False,
                    interactive_bootstrap_active=False,
                )
            )
            out.extend(
                _output_system_messages(
                    inner_tick_turn=False,
                    tick_proactive=False,
                    tools_on=True,
                    tool_side_compact=True,
                    async_foreground_chat_stack=False,
                    interactive_bootstrap_active=False,
                    include_significance_perception_slice=False,
                    chat_branch_no_tool_api=False,
                )
            )
            extend_contextual_system_slices(
                out,
                turn_compose_context_for_user_turn_tool_leg(
                    bundle=ctx.bundle,
                    context_meta=ctx.context_meta,
                ),
            )
        case _ as unexpected:
            raise AssertionError(
                f"compose_system_prefix unsupported recipe key={unexpected!r}"
            )
    return out


def compose_system_prefix_for_self_contained_track(
    bundle: PromptBundle,
    context: ContextMeta,
    store: MemoryStore,
    track: CompanionTurnTrack,
) -> list[dict[str, Any]]:
    """MONOLOG or AUTONOMY async tool path; core stack only."""
    match track:
        case CompanionTurnTrack.INNER_TICK_MONOLOG | CompanionTurnTrack.INNER_TICK_AUTONOMY:
            pass
        case _ as unexpected:
            raise AssertionError(
                f"compose_system_prefix_for_self_contained_track unsupported "
                f"track={unexpected!r}"
            )
    ctx = build_turn_compose_context(
        bundle=bundle,
        context_meta=context,
        runtime_context=default_runtime_context_for_compose(),
        store=store,
        track=track,
        phase=Phase.SETTLED,
        leg_kind=PromptLegKind.SINGLE_LLM,
        ai_private_text="",
        proactive_life_currents_block=None,
    )
    return compose_system_prefix(ctx)


def compose_system_prefix_for_user_chat_leg(
    bundle: PromptBundle,
    context: ContextMeta,
    leg_kind: PromptLegKind,
) -> list[dict[str, Any]]:
    """Settled USER_CHAT dual-LLM CHAT_LEG or TOOL_LEG; core only."""
    match leg_kind:
        case PromptLegKind.CHAT_LEG:
            ctx = turn_compose_context_for_user_turn_chat_leg(
                bundle=bundle,
                context_meta=context,
                phase=Phase.SETTLED,
            )
        case PromptLegKind.TOOL_LEG:
            ctx = turn_compose_context_for_user_turn_tool_leg(
                bundle=bundle,
                context_meta=context,
            )
        case _ as unexpected:
            raise AssertionError(
                f"compose_system_prefix_for_user_chat_leg unsupported "
                f"leg_kind={unexpected!r}"
            )
    return compose_system_prefix(ctx)
