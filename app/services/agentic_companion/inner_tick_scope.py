"""ORM scope resolution for inner-tick glue (user, agent, chat row, model)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from loguru import logger
from sqlalchemy import select

from app.core.companion_harness.agent_channel.scope import (
    AgentScope,
    is_agent_scope_memory_store_chat_id,
)
from app.core.config import global_config_loaded_from_config_yaml
from app.core.model_selection import select_chat_model
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services import chat_service
from app.core.companion_harness.companion.runtime_channel import ChannelKind
from app.services.agentic_companion.session import Coordinator, InnerTickCoords
from app.utils.models_catalog import GenAIModel, resolve_chat_text_model


class InnerTickModelSource(StrEnum):
    """Which model id to bind when resolving scope for an inner-tick fire attempt."""

    CHAT_DEFAULT = "chat_default"
    DREAMING_HARNESS = "dreaming_harness"


class InnerTickChatResolveMode(StrEnum):
    """Whether scope resolution may create a missing ``chats`` row."""

    GET_OR_CREATE = "get_or_create"
    READ_ONLY = "read_only"


@dataclass(frozen=True)
class InnerTickFireInput:
    """Bundled arguments for one inner-tick ``try_fire_*`` attempt on a presence wire."""

    runtime_channel: ChannelKind
    # Channel for TurnRuntimeContext; outbound delivery is pump-owned.

    coords: InnerTickCoords
    coordinator: Coordinator
    ws_conn_id: str
    tc_box: list[Any | None]


@dataclass(frozen=True)
class InnerTickScopeCoords:
    """Resolved DB scope for inner-tick fire paths (user, agent, chat, model)."""

    user_id: str
    agent_id: str
    chat_row_id: str | int
    chat_row_agent_id: str
    model_override: GenAIModel


async def resolve_inner_tick_scope_coords(
    fire_input: InnerTickFireInput,
    *,
    model_source: InnerTickModelSource,
) -> InnerTickScopeCoords | None:
    """Load user/chat and model for one presence inner-tick attempt."""
    return await resolve_inner_tick_scope_coords_for_triple(
        coords=fire_input.coords,
        poll_source=fire_input.ws_conn_id,
        model_source=model_source,
        chat_resolve_mode=InnerTickChatResolveMode.GET_OR_CREATE,
    )


async def resolve_inner_tick_scope_coords_for_triple(
    *,
    coords: InnerTickCoords,
    poll_source: str,
    model_source: InnerTickModelSource,
    chat_resolve_mode: InnerTickChatResolveMode,
) -> InnerTickScopeCoords | None:
    """Load user/chat and model for one scope triple (presence or scope worker)."""
    user_id = coords.user_id
    agent_id = coords.agent_id
    chat_id_str = str(coords.chat_id)

    async with AsyncSessionLocal() as pre_db:
        r_user = await pre_db.execute(select(User).where(User.id == user_id))
        current_user = r_user.scalar_one_or_none()
        if current_user is None:
            return None

        match model_source:
            case InnerTickModelSource.DREAMING_HARNESS:
                dreaming_llm = (
                    global_config_loaded_from_config_yaml.agent.companion_harness.dreaming_llm
                )
                model_override = resolve_chat_text_model(dreaming_llm)
            case InnerTickModelSource.CHAT_DEFAULT:
                model_override = select_chat_model(
                    user=current_user,
                    is_subscribed=False,
                )

        if is_agent_scope_memory_store_chat_id(chat_id_str):
            expected = AgentScope(
                user_id=user_id,
                agent_id=agent_id,
            ).memory_store_chat_id()
            if chat_id_str != expected:
                logger.debug(
                    "inner_tick_scope agent-scope chat_id mismatch poll_source={} "
                    "ctx={} expected={}",
                    poll_source,
                    chat_id_str,
                    expected,
                )
                return None
            return InnerTickScopeCoords(
                user_id=user_id,
                agent_id=agent_id,
                chat_row_id=chat_id_str,
                chat_row_agent_id=agent_id,
                model_override=model_override,
            )

        match chat_resolve_mode:
            case InnerTickChatResolveMode.GET_OR_CREATE:
                chat = await chat_service.get_or_create_chat_by_agent(
                    db=pre_db, user_id=user_id, agent_id=agent_id
                )
            case InnerTickChatResolveMode.READ_ONLY:
                chat = await chat_service.get_chat_by_user_and_agent(
                    pre_db, user_id, agent_id
                )
                if chat is None:
                    return None

        if str(chat.id) != chat_id_str:
            logger.debug(
                "inner_tick_scope chat_id mismatch poll_source={} ctx={} db_chat_id={}",
                poll_source,
                chat_id_str,
                chat.id,
            )
            return None

        return InnerTickScopeCoords(
            user_id=user_id,
            agent_id=agent_id,
            chat_row_id=chat.id,
            chat_row_agent_id=chat.agent_id,
            model_override=model_override,
        )
