"""Tests for ``compose_system_prefix`` recipe keys."""

from __future__ import annotations

import hashlib

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
    TurnComposeContext,
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
GOLDEN_MONOLOG_CONTENT_SHA256_PREFIX = "4b7353a7f5cabc59"
GOLDEN_AUTONOMY_CONTENT_SHA256_PREFIX = "0acf7778375465e1"
GOLDEN_CHAT_CONTENT_SHA256_PREFIX = "cc7d72684a310f98"
GOLDEN_TOOL_CONTENT_SHA256_PREFIX = "14c06d0421d00c0b"


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


def _content_sha256_prefix(contents: list[str]) -> str:
    joined = "\n---\n".join(contents)
    return hashlib.sha256(joined.encode()).hexdigest()[:16]


def _ctx(
    *,
    bundle: PromptBundle,
    context: ContextMeta,
    store: MemoryStore,
    track: CompanionTurnTrack,
    leg_kind: PromptLegKind,
) -> TurnComposeContext:
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
    assert _content_sha256_prefix(from_ctx) == GOLDEN_MONOLOG_CONTENT_SHA256_PREFIX
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
    assert _content_sha256_prefix(from_ctx) == GOLDEN_AUTONOMY_CONTENT_SHA256_PREFIX


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
    assert _content_sha256_prefix(from_ctx) == GOLDEN_CHAT_CONTENT_SHA256_PREFIX


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
    assert _content_sha256_prefix(from_ctx) == GOLDEN_TOOL_CONTENT_SHA256_PREFIX
