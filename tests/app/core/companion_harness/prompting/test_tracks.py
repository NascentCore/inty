"""Byte-identical equivalence tests for track-composed user_turn assembly."""

from __future__ import annotations

from app.core.companion_harness.companion.models import (
    ContextMeta,
    InnerTickActivity,
)
from app.core.companion_harness.companion.prompts.system_messages import (
    build_system_messages,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
    TurnRuntimeContext,
)
from app.core.companion_harness.experience_profile.experience_directives import (
    ExperienceDirectiveTone,
    ExperienceDirectives,
    ExperienceSessionIntent,
)
from app.core.companion_harness.prompt_builder import PromptBuilder
from app.core.companion_harness.prompting.bundle import PromptBundle
from app.core.companion_harness.prompting.tracks import (
    build_settled_user_turn_dual_chat_leg_system_messages,
)


def _runtime_context() -> TurnRuntimeContext:
    return TurnRuntimeContext(
        channel=ChannelKind.APP_WS,
        implicit_signal_bundle=None,
    )


def _bundle() -> PromptBundle:
    return PromptBundle(
        identity="identity\n",
        soul="soul\n",
        style_md="style\n",
        user_md="user\n",
        memory_md="memory\n",
        memory_daily_today_md="daily gist\n",
        tools_md="# Tools\ngenerate_image rules\n",
        harness_md="# Harness\n",
        channels_md="# Channels\n",
        significance_perception_md="# Significance\n",
        companionship_md="ship\n",
    )


def test_settled_single_llm_matches_legacy_build_system_messages() -> None:
    bundle = _bundle()
    context = ContextMeta(
        context_mode="intimate",
        experience_directives=ExperienceDirectives(
            intent=ExperienceSessionIntent.DEEP_CONVERSATION,
            tone=ExperienceDirectiveTone.WARM,
        ),
    )
    legacy = build_system_messages(
        bundle,
        context,
        enable_tools=True,
        inner_tick_turn=False,
        inner_tick_activity=InnerTickActivity.MONOLOG,
    )
    builder = PromptBuilder(
        bundle=bundle,
        context=context,
        runtime_context=_runtime_context(),
    )
    composed = builder.settled_single_llm_system_messages()
    assert composed == legacy


def test_settled_dual_chat_leg_matches_legacy_build_system_messages() -> None:
    bundle = _bundle()
    context = ContextMeta()
    legacy = build_system_messages(
        bundle,
        context,
        enable_tools=True,
        inner_tick_turn=False,
        inner_tick_activity=InnerTickActivity.MONOLOG,
        async_foreground_chat_stack=True,
        include_significance_perception_slice=True,
    )
    composed = build_settled_user_turn_dual_chat_leg_system_messages(
        bundle,
        context,
    )
    assert composed == legacy
