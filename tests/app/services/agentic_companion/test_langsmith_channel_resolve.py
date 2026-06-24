"""Tests for ``resolve_langsmith_slice_for_session``."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.langsmith_turn_slice import (
    LangsmithChannelSource,
)
from app.core.companion_harness.agent_channel.channel_kind import (
    ChannelKind,
)
from app.services.agentic_channel.channel_runtime import (
    ChannelRuntimeState,
    clear_registries_for_tests,
    get_scope_channel_registry,
)
from app.services.agentic_companion.langsmith_channel_resolve import (
    resolve_langsmith_slice_for_session,
)
from app.services.agentic_companion.active_channel_registry import (
    clear_all_for_tests,
    register_active_channel,
)


@pytest.fixture(autouse=True)
def _clear_channel_state() -> None:
    clear_registries_for_tests()
    clear_all_for_tests()


def _session(*, user_id: str, companion_id: str, chat_id: str) -> MagicMock:
    session = MagicMock()
    session.user_id = user_id
    session.companion_id = companion_id
    session.chat_id = chat_id
    return session


@pytest.mark.asyncio
async def test_resolve_uses_scope_registry_for_agent_scope_chat_id() -> None:
    scope = AgentScope(user_id="u1", agent_id="a1")
    registry = get_scope_channel_registry(scope)
    registry.states[ChannelKind.TELEGRAM] = ChannelRuntimeState.ACTIVE
    session = _session(
        user_id="u1",
        companion_id="a1",
        chat_id=scope.memory_store_chat_id(),
    )

    slice_ = resolve_langsmith_slice_for_session(session)

    assert slice_.runtime_channel == ChannelKind.TELEGRAM
    assert slice_.channel_source == LangsmithChannelSource.SCOPE_REGISTRY


@pytest.mark.asyncio
async def test_resolve_uses_user_registry_for_ws_chat_id() -> None:
    register_active_channel(user_id="u-ws", channel=ChannelKind.APP_WS,
    )
    session = _session(user_id="u-ws", companion_id="a1", chat_id="chat-uuid-1")

    slice_ = resolve_langsmith_slice_for_session(session)

    assert slice_.runtime_channel == ChannelKind.APP_WS
    assert slice_.channel_source == LangsmithChannelSource.USER_REGISTRY


def test_resolve_defaults_to_app_when_no_registry_entry() -> None:
    session = _session(
        user_id="u-empty", companion_id="a1", chat_id="chat-uuid-2"
    )

    slice_ = resolve_langsmith_slice_for_session(session)

    assert slice_.runtime_channel == ChannelKind.APP_WS
    assert slice_.channel_source == LangsmithChannelSource.DEFAULT_APP


def test_resolve_agent_scope_without_active_channel_defaults_app() -> None:
    scope = AgentScope(user_id="u2", agent_id="a2")
    session = _session(
        user_id="u2",
        companion_id="a2",
        chat_id=scope.memory_store_chat_id(),
    )

    slice_ = resolve_langsmith_slice_for_session(session)

    assert slice_.runtime_channel == ChannelKind.APP_WS
    assert slice_.channel_source == LangsmithChannelSource.DEFAULT_APP


def test_resolve_agent_scope_without_active_channel_logs_debug() -> None:
    from loguru import logger

    scope = AgentScope(user_id="u3", agent_id="a3")
    session = _session(
        user_id="u3",
        companion_id="a3",
        chat_id=scope.memory_store_chat_id(),
    )
    messages: list[str] = []
    sink_id = logger.add(messages.append, level="DEBUG", format="{message}")

    try:
        resolve_langsmith_slice_for_session(session)
    finally:
        logger.remove(sink_id)

    assert any(
        "langsmith_channel_resolve agent_scope_default_app" in line
        and scope.registry_key() in line
        for line in messages
    )
