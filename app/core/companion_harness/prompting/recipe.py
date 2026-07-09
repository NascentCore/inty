"""Track × phase × leg recipes for production system-prefix core stack assembly.

``compose_system_prefix`` routes (track, phase, leg_kind) to the per-track
``build_system_messages_for_*`` implementations. Peripheral slices (channel
output format, Weixin alias, reply-language) stay at callers; see
``prompt_stack.append_peripheral_system_slices``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    ContextMeta,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.prompting.bundle import PromptBundle
from app.core.companion_harness.prompting.compose_context import TurnComposeContext
from app.core.companion_harness.prompting.leg_kind import PromptLegKind
from app.core.companion_harness.prompting.phase import Phase
from app.core.companion_harness.prompting.system_messages import (
    build_system_messages_for_inner_tick_autonomy,
    build_system_messages_for_inner_tick_monolog,
    build_system_messages_for_tool_track,
)
from app.core.companion_harness.prompting.tracks import (
    build_settled_user_turn_dual_chat_leg_system_messages,
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
    """Route one registered (track, phase, leg_kind) recipe to its builder."""
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
    match key:
        case TrackSystemRecipeKey(
            CompanionTurnTrack.INNER_TICK_MONOLOG,
            Phase.SETTLED,
            PromptLegKind.SINGLE_LLM,
        ):
            return build_system_messages_for_inner_tick_monolog(
                ctx.bundle,
                ctx.context_meta,
                ctx.store,
            )
        case TrackSystemRecipeKey(
            CompanionTurnTrack.INNER_TICK_AUTONOMY,
            Phase.SETTLED,
            PromptLegKind.SINGLE_LLM,
        ):
            return build_system_messages_for_inner_tick_autonomy(
                ctx.bundle,
                ctx.context_meta,
                ctx.store,
            )
        case TrackSystemRecipeKey(
            CompanionTurnTrack.USER_CHAT,
            Phase.SETTLED,
            PromptLegKind.CHAT_LEG,
        ):
            return build_settled_user_turn_dual_chat_leg_system_messages(
                ctx.bundle,
                ctx.context_meta,
                phase=Phase.SETTLED,
            )
        case TrackSystemRecipeKey(
            CompanionTurnTrack.USER_CHAT,
            Phase.SETTLED,
            PromptLegKind.TOOL_LEG,
        ):
            return build_system_messages_for_tool_track(
                ctx.bundle,
                ctx.context_meta,
            )
        case _ as unexpected:
            raise AssertionError(
                f"compose_system_prefix unsupported recipe key={unexpected!r}"
            )


def compose_system_prefix_for_self_contained_track(
    bundle: PromptBundle,
    context: ContextMeta,
    store: MemoryStore,
    track: CompanionTurnTrack,
) -> list[dict[str, Any]]:
    """MONOLOG or AUTONOMY async tool path; core stack only."""
    match track:
        case CompanionTurnTrack.INNER_TICK_MONOLOG:
            return build_system_messages_for_inner_tick_monolog(
                bundle,
                context,
                store,
            )
        case CompanionTurnTrack.INNER_TICK_AUTONOMY:
            return build_system_messages_for_inner_tick_autonomy(
                bundle,
                context,
                store,
            )
        case _ as unexpected:
            raise AssertionError(
                f"compose_system_prefix_for_self_contained_track unsupported "
                f"track={unexpected!r}"
            )


def compose_system_prefix_for_user_chat_leg(
    bundle: PromptBundle,
    context: ContextMeta,
    leg_kind: PromptLegKind,
) -> list[dict[str, Any]]:
    """Settled USER_CHAT dual-LLM CHAT_LEG or TOOL_LEG; core only."""
    match leg_kind:
        case PromptLegKind.CHAT_LEG:
            return build_settled_user_turn_dual_chat_leg_system_messages(
                bundle,
                context,
                phase=Phase.SETTLED,
            )
        case PromptLegKind.TOOL_LEG:
            return build_system_messages_for_tool_track(
                bundle,
                context,
            )
        case _ as unexpected:
            raise AssertionError(
                f"compose_system_prefix_for_user_chat_leg unsupported "
                f"leg_kind={unexpected!r}"
            )
