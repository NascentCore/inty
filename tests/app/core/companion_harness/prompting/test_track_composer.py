"""Tests for ``TrackPromptComposer`` chat-only track routing."""

from __future__ import annotations

from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    ContextMeta,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.prompt_builder import PromptBuilder
from app.core.companion_harness.prompting.bundle import PromptBundle
from app.core.companion_harness.prompting.compose_context import (
    TurnComposeContext,
    build_turn_compose_context,
)
from app.core.companion_harness.prompting.leg_kind import PromptLegKind
from app.core.companion_harness.prompting.track_composer import TrackPromptComposer
from app.core.companion_harness.prompting.phase import resolve_compose_phase


def _bundle() -> PromptBundle:
    return PromptBundle(
        identity="identity",
        soul="soul",
        style_md="style",
        user_md="user",
        memory_md="",
    )


def _turn_ctx(
    *,
    store: MemoryStore,
    track: CompanionTurnTrack,
) -> TurnComposeContext:
    context_meta = ContextMeta()
    return build_turn_compose_context(
        bundle=_bundle(),
        context_meta=context_meta,
        runtime_context=TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=None,
        ),
        store=store,
        track=track,
        phase=resolve_compose_phase(context_meta),
        leg_kind=PromptLegKind.SINGLE_LLM,
        ai_private_text="",
        proactive_life_currents_block=None,
    )


def test_system_dicts_for_track_greeting_matches_prompt_builder(tmp_path) -> None:
    store = MemoryStore(
        scope=CompanionScope("tc-greeting", "agent", tmp_path.name),
        repository=None,
    )
    turn_ctx = _turn_ctx(
        store=store,
        track=CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING,
    )
    builder = PromptBuilder(
        bundle=turn_ctx.bundle,
        context=turn_ctx.context_meta,
        runtime_context=turn_ctx.runtime_context,
    )
    assert TrackPromptComposer().system_dicts_for_track(
        CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING,
        turn_ctx,
    ) == builder.greeting_system_dicts()


def test_system_dicts_for_track_proactive_matches_prompt_builder(tmp_path) -> None:
    store = MemoryStore(
        scope=CompanionScope("tc-proactive", "agent", tmp_path.name),
        repository=None,
    )
    turn_ctx = _turn_ctx(
        store=store,
        track=CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT,
    )
    builder = PromptBuilder(
        bundle=turn_ctx.bundle,
        context=turn_ctx.context_meta,
        runtime_context=turn_ctx.runtime_context,
    )
    assert TrackPromptComposer().system_dicts_for_track(
        CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT,
        turn_ctx,
    ) == builder.proactive_system_dicts(store)


def test_system_dicts_for_track_scheduled_matches_prompt_builder(tmp_path) -> None:
    store = MemoryStore(
        scope=CompanionScope("tc-scheduled", "agent", tmp_path.name),
        repository=None,
    )
    turn_ctx = _turn_ctx(
        store=store,
        track=CompanionTurnTrack.INNER_TICK_SCHEDULED,
    )
    builder = PromptBuilder(
        bundle=turn_ctx.bundle,
        context=turn_ctx.context_meta,
        runtime_context=turn_ctx.runtime_context,
    )
    assert TrackPromptComposer().system_dicts_for_track(
        CompanionTurnTrack.INNER_TICK_SCHEDULED,
        turn_ctx,
    ) == builder.scheduled_system_dicts(store)
