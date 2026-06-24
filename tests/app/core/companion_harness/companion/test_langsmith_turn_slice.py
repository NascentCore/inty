"""Tests for ``CompanionTurnLangsmithSlice``."""

from __future__ import annotations

from app.core.companion_harness.companion.langsmith_turn_slice import (
    CompanionTurnLangsmithSlice,
    LangsmithChannelSource,
)
from app.core.companion_harness.agent_channel.channel_kind import (
    ChannelKind,
    TurnRuntimeContext,
)
from app.core.companion_harness.llm.langsmith_invocation_extra import (
    INTY_LLM_SOURCE_METADATA_KEY,
    INTY_RUNTIME_CHANNEL_METADATA_KEY,
    INTY_RUNTIME_CHANNEL_SOURCE_METADATA_KEY,
    SOURCE_FOREGROUND_DUAL_LLM_ENVELOPE,
    SOURCE_TOOL_BACKGROUND_INITIAL,
)


def test_from_runtime_context_uses_explicit_turn_source() -> None:
    slice_ = CompanionTurnLangsmithSlice.from_runtime_context(
        TurnRuntimeContext(
            channel=ChannelKind.TELEGRAM,
            implicit_signal_bundle=None,
        )
    )
    assert slice_.runtime_channel == ChannelKind.TELEGRAM
    assert slice_.channel_source == LangsmithChannelSource.EXPLICIT_TURN


def test_app_default_tags_app_with_default_source() -> None:
    slice_ = CompanionTurnLangsmithSlice.app_default()
    assert slice_.runtime_channel == ChannelKind.APP_WS
    assert slice_.channel_source == LangsmithChannelSource.DEFAULT_APP
    assert slice_.parent_tags() == ["runtime_channel_app_ws"]
    meta = slice_.parent_metadata_fragment()
    assert meta[INTY_RUNTIME_CHANNEL_METADATA_KEY] == "app_ws"
    assert meta[INTY_RUNTIME_CHANNEL_SOURCE_METADATA_KEY] == "default_app"


def test_foreground_invocation_extra_merges_channel_and_source() -> None:
    slice_ = CompanionTurnLangsmithSlice.from_channel(
        ChannelKind.WECHAT_WEIXIN,
        LangsmithChannelSource.SCOPE_REGISTRY,
    )
    extra = slice_.foreground_invocation_extra(
        source=SOURCE_FOREGROUND_DUAL_LLM_ENVELOPE,
        extra_metadata=None,
    )
    meta = extra["metadata"]
    assert (
        meta[INTY_LLM_SOURCE_METADATA_KEY]
        == SOURCE_FOREGROUND_DUAL_LLM_ENVELOPE
    )
    assert meta[INTY_RUNTIME_CHANNEL_METADATA_KEY] == "wechat_weixin"
    assert meta[INTY_RUNTIME_CHANNEL_SOURCE_METADATA_KEY] == "scope_registry"


def test_tool_call_extra_includes_channel_metadata() -> None:
    slice_ = CompanionTurnLangsmithSlice.app_default()
    extra = slice_.tool_call_extra(
        phase_suffix=SOURCE_TOOL_BACKGROUND_INITIAL,
        extra_metadata=None,
    )
    assert extra["name"] == SOURCE_TOOL_BACKGROUND_INITIAL
    assert extra["metadata"][INTY_RUNTIME_CHANNEL_METADATA_KEY] == "app_ws"


def test_dreaming_consolidation_extra_preserves_role_name() -> None:
    slice_ = CompanionTurnLangsmithSlice.from_channel(
        ChannelKind.TELEGRAM,
        LangsmithChannelSource.SCOPE_REGISTRY,
    )
    extra = slice_.dreaming_consolidation_extra(model_role="memory")
    assert extra["name"] == "agentic_companion_dreaming_consolidation-memory"
    assert extra["metadata"][INTY_RUNTIME_CHANNEL_METADATA_KEY] == "telegram"
    assert (
        extra["metadata"][INTY_LLM_SOURCE_METADATA_KEY]
        == "dreaming_consolidation_memory"
    )
