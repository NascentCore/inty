"""Immutable per-turn inputs for prompt system-prefix assembly.

``TurnComposeContext`` is the routing fact carrier: track, phase, and derived
``compose_trigger`` / ``inner_tick_activity`` gate contextual slice inclusion.
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
    ChannelKind,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.prompting.bundle import PromptBundle
from app.core.companion_harness.prompting.compose_trigger import (
    PromptComposeTrigger,
    compose_trigger_for_track,
)
from app.core.companion_harness.prompting.leg_kind import PromptLegKind
from app.core.companion_harness.prompting.phase import (
    Phase,
    resolve_phase_for_compose,
)


@dataclass(frozen=True)
class TurnComposeContext:
    """Immutable inputs for one system-prefix compose invocation."""

    # MemDoc bundle for the active companion scope.
    bundle: PromptBundle
    # Session metadata including bootstrap completion and experience profile.
    context_meta: ContextMeta
    # Active gateway channel and implicit-signal payload for peripheral slices.
    runtime_context: TurnRuntimeContext
    # MemoryStore handle; contextual reads use proactive LIFE_CURRENTS when wired.
    store: MemoryStore
    # Production turn track; drives compose_trigger and inner-tick activity derivation.
    track: CompanionTurnTrack
    # Bootstrap vs settled phase within the track.
    phase: Phase
    # LLM leg variant; Phase 1 always SINGLE_LLM.
    leg_kind: PromptLegKind
    # MONOLOG contextual payload; empty when track is not monolog.
    ai_private_text: str
    # PROACTIVE_CHAT LIFE_CURRENTS hint body; None when not injected.
    proactive_life_currents_block: str | None
    # Derived from track; gates ABOUT.md injection.
    compose_trigger: PromptComposeTrigger
    # Derived from track via inner_tick_kind registry; None for user-facing tracks.
    inner_tick_activity: InnerTickActivity | None


def _derive_inner_tick_activity(
    track: CompanionTurnTrack,
) -> InnerTickActivity | None:
    match track:
        case CompanionTurnTrack.INNER_TICK_MONOLOG:
            return InnerTickActivity.MONOLOG
        case CompanionTurnTrack.INNER_TICK_AUTONOMY:
            return InnerTickActivity.AUTONOMY
        case (
            CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT
            | CompanionTurnTrack.INNER_TICK_SCHEDULED
        ):
            return InnerTickActivity.PROACTIVE_CHAT
        case _:
            return None


def build_turn_compose_context(
    *,
    bundle: PromptBundle,
    context_meta: ContextMeta,
    runtime_context: TurnRuntimeContext,
    store: MemoryStore,
    track: CompanionTurnTrack,
    phase: Phase,
    leg_kind: PromptLegKind,
    ai_private_text: str,
    proactive_life_currents_block: str | None,
) -> TurnComposeContext:
    """Construct ctx with derived compose_trigger and inner_tick_activity."""
    return TurnComposeContext(
        bundle=bundle,
        context_meta=context_meta,
        runtime_context=runtime_context,
        store=store,
        track=track,
        phase=phase,
        leg_kind=leg_kind,
        ai_private_text=ai_private_text,
        proactive_life_currents_block=proactive_life_currents_block,
        compose_trigger=compose_trigger_for_track(track),
        inner_tick_activity=_derive_inner_tick_activity(track),
    )


def empty_memory_store_for_compose() -> MemoryStore:
    """Fake MemoryStore when contextual assembly does not read MemDocs."""
    return MemoryStore(
        scope=CompanionScope("compose", "ctx", "noop"),
        repository=None,
    )


def default_runtime_context_for_compose() -> TurnRuntimeContext:
    """Default gateway context for legacy paths without channel signals."""
    return TurnRuntimeContext(
        channel=ChannelKind.APP_WS,
        implicit_signal_bundle=None,
    )


def extend_contextual_system_slices(
    out: list[dict[str, Any]],
    ctx: TurnComposeContext,
) -> None:
    """Append contextual category slices; lazy-imports contextual to break cycle."""
    # TODO(#3453): Inline after slice builders move out of system_messages.
    from app.core.companion_harness.prompting.contextual import (
        assemble_contextual_slices,
    )

    out.extend(assemble_contextual_slices(ctx))


def turn_compose_context_for_self_contained_track(
    *,
    bundle: PromptBundle,
    context_meta: ContextMeta,
    store: MemoryStore,
    track: CompanionTurnTrack,
    ai_private_text: str,
    proactive_life_currents_block: str | None,
) -> TurnComposeContext:
    """Construct ctx for inlined per-track builders (tool / monolog / autonomy)."""
    return build_turn_compose_context(
        bundle=bundle,
        context_meta=context_meta,
        runtime_context=default_runtime_context_for_compose(),
        store=store,
        track=track,
        phase=resolve_phase_for_compose(track, context_meta),
        leg_kind=PromptLegKind.SINGLE_LLM,
        ai_private_text=ai_private_text,
        proactive_life_currents_block=proactive_life_currents_block,
    )


def turn_compose_context_for_user_turn_chat_leg(
    *,
    bundle: PromptBundle,
    context_meta: ContextMeta,
    phase: Phase,
) -> TurnComposeContext:
    """Dual-LLM chat leg user-turn contextual; no MemoryStore reads."""
    return build_turn_compose_context(
        bundle=bundle,
        context_meta=context_meta,
        runtime_context=default_runtime_context_for_compose(),
        store=empty_memory_store_for_compose(),
        track=CompanionTurnTrack.USER_CHAT,
        phase=phase,
        leg_kind=PromptLegKind.CHAT_LEG,
        ai_private_text="",
        proactive_life_currents_block=None,
    )


def turn_compose_context_for_user_turn_tool_leg(
    *,
    bundle: PromptBundle,
    context_meta: ContextMeta,
) -> TurnComposeContext:
    """Dual-LLM tool leg; USER_CHAT track, SETTLED phase, no MemoryStore reads."""
    return build_turn_compose_context(
        bundle=bundle,
        context_meta=context_meta,
        runtime_context=default_runtime_context_for_compose(),
        store=empty_memory_store_for_compose(),
        track=CompanionTurnTrack.USER_CHAT,
        phase=Phase.SETTLED,
        leg_kind=PromptLegKind.TOOL_LEG,
        ai_private_text="",
        proactive_life_currents_block=None,
    )


def turn_compose_context_from_legacy_flags(
    *,
    bundle: PromptBundle,
    context_meta: ContextMeta,
    runtime_context: TurnRuntimeContext,
    store: MemoryStore,
    track: CompanionTurnTrack,
    inner_tick_turn: bool,
    inner_tick_activity: InnerTickActivity,
    ai_private_text: str,
    proactive_life_currents_block: str | None,
    interactive_bootstrap_active: bool,
) -> TurnComposeContext:
    """Bridge ``build_system_messages`` bool flags to ``TurnComposeContext``."""
    if interactive_bootstrap_active:
        phase = Phase.BOOTSTRAP
    else:
        phase = resolve_phase_for_compose(track, context_meta)
    derived_activity = _derive_inner_tick_activity(track)
    if derived_activity is None:
        assert not inner_tick_turn
    else:
        assert inner_tick_turn
        assert inner_tick_activity == derived_activity
    return build_turn_compose_context(
        bundle=bundle,
        context_meta=context_meta,
        runtime_context=runtime_context,
        store=store,
        track=track,
        phase=phase,
        leg_kind=PromptLegKind.SINGLE_LLM,
        ai_private_text=ai_private_text,
        proactive_life_currents_block=proactive_life_currents_block,
    )
