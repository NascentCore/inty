"""Tests for ``TurnComposeContext`` and compose-trigger derivation."""

from __future__ import annotations

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
from app.core.companion_harness.prompting.compose_context import (
    build_turn_compose_context,
    turn_compose_context_from_legacy_flags,
)
from app.core.companion_harness.prompting.compose_trigger import (
    PromptComposeTrigger,
    compose_trigger_for_track,
)
from app.core.companion_harness.prompting.leg_kind import PromptLegKind
from app.core.companion_harness.prompting.phase import Phase, resolve_phase_for_compose


def _store(tmp_path) -> MemoryStore:
    return MemoryStore(
        scope=CompanionScope("compose-ctx", "agent", tmp_path.name),
        repository=None,
    )


def _bundle() -> PromptBundle:
    return PromptBundle(
        identity="id",
        soul="soul",
        style_md="style",
        user_md="user",
        memory_md="",
    )


def test_compose_trigger_user_chat_tracks() -> None:
    assert (
        compose_trigger_for_track(CompanionTurnTrack.USER_CHAT)
        == PromptComposeTrigger.USER_MESSAGE
    )
    assert (
        compose_trigger_for_track(CompanionTurnTrack.USER_CHAT_BOOTSTRAP)
        == PromptComposeTrigger.USER_MESSAGE
    )
    assert (
        compose_trigger_for_track(CompanionTurnTrack.INNER_TICK_MONOLOG)
        == PromptComposeTrigger.SYSTEM_INITIATED
    )
    assert (
        compose_trigger_for_track(CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING)
        == PromptComposeTrigger.SYSTEM_INITIATED
    )


def test_inner_tick_activity_derived_from_track(tmp_path) -> None:
    ctx = build_turn_compose_context(
        bundle=_bundle(),
        context_meta=ContextMeta(),
        runtime_context=TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=None,
        ),
        store=_store(tmp_path),
        track=CompanionTurnTrack.INNER_TICK_MONOLOG,
        phase=Phase.SETTLED,
        leg_kind=PromptLegKind.SINGLE_LLM,
        ai_private_text="",
        proactive_life_currents_block=None,
    )
    assert ctx.inner_tick_activity == InnerTickActivity.MONOLOG

    user_ctx = build_turn_compose_context(
        bundle=_bundle(),
        context_meta=ContextMeta(),
        runtime_context=TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=None,
        ),
        store=_store(tmp_path),
        track=CompanionTurnTrack.USER_CHAT,
        phase=Phase.SETTLED,
        leg_kind=PromptLegKind.SINGLE_LLM,
        ai_private_text="",
        proactive_life_currents_block=None,
    )
    assert user_ctx.inner_tick_activity is None


def test_resolve_phase_for_compose_user_chat_bootstrap_pins_bootstrap() -> None:
    """``USER_CHAT_BOOTSTRAP`` track always composes bootstrap contextual slices."""
    settled_context = ContextMeta(
        workspace_bootstrap_user_interactive_completed=True,
    )
    assert (
        resolve_phase_for_compose(
            CompanionTurnTrack.USER_CHAT_BOOTSTRAP,
            settled_context,
        )
        == Phase.BOOTSTRAP
    )


def test_legacy_flags_use_track_pinned_bootstrap_phase(tmp_path) -> None:
    """``USER_CHAT_BOOTSTRAP`` stays bootstrap when legacy bool flag is false."""
    ctx = turn_compose_context_from_legacy_flags(
        bundle=_bundle(),
        context_meta=ContextMeta(
            workspace_bootstrap_user_interactive_completed=True,
        ),
        runtime_context=TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=None,
        ),
        store=_store(tmp_path),
        track=CompanionTurnTrack.USER_CHAT_BOOTSTRAP,
        inner_tick_turn=False,
        inner_tick_activity=InnerTickActivity.MONOLOG,
        ai_private_text="",
        proactive_life_currents_block=None,
        interactive_bootstrap_active=False,
    )
    assert ctx.phase == Phase.BOOTSTRAP
