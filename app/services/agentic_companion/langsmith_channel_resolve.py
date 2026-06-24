"""Resolve ``CompanionTurnLangsmithSlice`` for session-background LangSmith runs."""

from __future__ import annotations

from loguru import logger

from app.core.companion_harness.agent_channel.scope import (
    AgentScope,
    is_agent_scope_memory_store_chat_id,
)
from app.core.companion_harness.companion.langsmith_turn_slice import (
    CompanionTurnLangsmithSlice,
    LangsmithChannelSource,
)
from app.core.companion_harness.companion.manager import CompanionSession
from app.core.companion_harness.agent_channel.channel_kind import (
    ChannelKind,
)
from app.services.agentic_channel.channel_runtime import (
    get_scope_channel_registry,
)
from app.services.agentic_companion.active_channel_registry import (
    active_channel_for_user,
)


def resolve_langsmith_slice_for_session(
    session: CompanionSession,
) -> CompanionTurnLangsmithSlice:
    """Infer human-facing channel for dreaming and other non-turn LangSmith parents."""
    chat_id = str(session.chat_id)
    if is_agent_scope_memory_store_chat_id(chat_id):
        scope = AgentScope(
            user_id=session.user_id,
            agent_id=session.companion_id,
        )
        active = get_scope_channel_registry(scope).active_channel()
        if active is not None:
            return CompanionTurnLangsmithSlice.from_channel(
                active,
                LangsmithChannelSource.SCOPE_REGISTRY,
            )
        logger.debug(
            "langsmith_channel_resolve agent_scope_default_app scope={}",
            scope.registry_key(),
        )
        return CompanionTurnLangsmithSlice.from_channel(
            ChannelKind.APP_WS,
            LangsmithChannelSource.DEFAULT_APP,
        )

    user_active = active_channel_for_user(session.user_id)
    if user_active is not None:
        return CompanionTurnLangsmithSlice.from_channel(
            user_active,
            LangsmithChannelSource.USER_REGISTRY,
        )

    return CompanionTurnLangsmithSlice.app_default()
