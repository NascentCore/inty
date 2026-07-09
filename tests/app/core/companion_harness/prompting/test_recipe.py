"""Tests for ``compose_system_prefix`` recipe keys."""

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
from app.core.companion_harness.prompting.bundle import PromptBundle
from app.core.companion_harness.prompting.compose_context import (
    build_turn_compose_context,
    default_runtime_context_for_compose,
    empty_memory_store_for_compose,
)
from app.core.companion_harness.prompting.leg_kind import PromptLegKind
from app.core.companion_harness.prompting.phase import Phase
from app.core.companion_harness.prompting.recipe import (
    compose_system_prefix,
    compose_system_prefix_for_self_contained_track,
    compose_system_prefix_for_user_chat_leg,
)

GOLDEN_MONOLOG_LINE_COUNT = 12
GOLDEN_AUTONOMY_LINE_COUNT = 10
GOLDEN_CHAT_LINE_COUNT = 14
GOLDEN_TOOL_LINE_COUNT = 15


def _store(tmp_path) -> MemoryStore:
    return MemoryStore(
        scope=CompanionScope("recipe", "agent", tmp_path.name),
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


def _system_contents(messages: list[dict]) -> list[str]:
    return [str(m["content"]) for m in messages if m["role"] == "system"]


def _ctx(
    *,
    bundle: PromptBundle,
    context: ContextMeta,
    store: MemoryStore,
    track: CompanionTurnTrack,
    leg_kind: PromptLegKind,
) -> object:
    return build_turn_compose_context(
        bundle=bundle,
        context_meta=context,
        runtime_context=TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=None,
        ),
        store=store,
        track=track,
        phase=Phase.SETTLED,
        leg_kind=leg_kind,
        ai_private_text="",
        proactive_life_currents_block=None,
    )


def test_monolog_recipe_matches_helper_and_golden_line_count(tmp_path) -> None:
    bundle = _bundle()
    context = ContextMeta()
    store = _store(tmp_path)
    ctx = _ctx(
        bundle=bundle,
        context=context,
        store=store,
        track=CompanionTurnTrack.INNER_TICK_MONOLOG,
        leg_kind=PromptLegKind.SINGLE_LLM,
    )
    from_ctx = _system_contents(compose_system_prefix(ctx))
    from_helper = _system_contents(
        compose_system_prefix_for_self_contained_track(
            bundle,
            context,
            store,
            CompanionTurnTrack.INNER_TICK_MONOLOG,
        )
    )
    assert from_ctx == from_helper
    assert len(from_ctx) == GOLDEN_MONOLOG_LINE_COUNT
    assert from_ctx[0].startswith("# Axiom")


def test_autonomy_recipe_matches_helper_and_golden_line_count(tmp_path) -> None:
    bundle = _bundle()
    context = ContextMeta()
    store = _store(tmp_path)
    ctx = _ctx(
        bundle=bundle,
        context=context,
        store=store,
        track=CompanionTurnTrack.INNER_TICK_AUTONOMY,
        leg_kind=PromptLegKind.SINGLE_LLM,
    )
    from_ctx = _system_contents(compose_system_prefix(ctx))
    from_helper = _system_contents(
        compose_system_prefix_for_self_contained_track(
            bundle,
            context,
            store,
            CompanionTurnTrack.INNER_TICK_AUTONOMY,
        )
    )
    assert from_ctx == from_helper
    assert len(from_ctx) == GOLDEN_AUTONOMY_LINE_COUNT


def test_dual_chat_leg_recipe_matches_helper_and_golden_line_count() -> None:
    bundle = _bundle()
    context = ContextMeta(context_mode="intimate")
    ctx = build_turn_compose_context(
        bundle=bundle,
        context_meta=context,
        runtime_context=default_runtime_context_for_compose(),
        store=empty_memory_store_for_compose(),
        track=CompanionTurnTrack.USER_CHAT,
        phase=Phase.SETTLED,
        leg_kind=PromptLegKind.CHAT_LEG,
        ai_private_text="",
        proactive_life_currents_block=None,
    )
    from_ctx = _system_contents(compose_system_prefix(ctx))
    from_helper = _system_contents(
        compose_system_prefix_for_user_chat_leg(
            bundle,
            context,
            PromptLegKind.CHAT_LEG,
        )
    )
    assert from_ctx == from_helper
    assert len(from_ctx) == GOLDEN_CHAT_LINE_COUNT


def test_dual_tool_leg_recipe_matches_helper_and_golden_line_count() -> None:
    bundle = _bundle()
    context = ContextMeta()
    ctx = build_turn_compose_context(
        bundle=bundle,
        context_meta=context,
        runtime_context=default_runtime_context_for_compose(),
        store=empty_memory_store_for_compose(),
        track=CompanionTurnTrack.USER_CHAT,
        phase=Phase.SETTLED,
        leg_kind=PromptLegKind.TOOL_LEG,
        ai_private_text="",
        proactive_life_currents_block=None,
    )
    from_ctx = _system_contents(compose_system_prefix(ctx))
    from_helper = _system_contents(
        compose_system_prefix_for_user_chat_leg(
            bundle,
            context,
            PromptLegKind.TOOL_LEG,
        )
    )
    assert from_ctx == from_helper
    assert len(from_ctx) == GOLDEN_TOOL_LINE_COUNT
