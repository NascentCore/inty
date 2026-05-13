"""
Review-only structured Agent data loader for future integration.
"""

from __future__ import annotations

from typing import Optional

from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.core.agent.clean_prompt_system import AgentPromptContext, AgentRuntimeSettings
from app.core.config import (
    global_config_loaded_from_config_yaml as global_config,
)
from app.services.cache_service import cache_service


def _build_agent_prompt_context_from_row(
    agent_id: str, row: tuple
) -> AgentPromptContext:
    raw_settings = row[3]
    settings: Optional[AgentRuntimeSettings] = None
    if raw_settings is not None:
        if not isinstance(raw_settings, dict):
            raise ValueError(
                f"Agent settings must be an object, got {type(raw_settings).__name__}"
            )
        settings = AgentRuntimeSettings.model_validate(raw_settings)

    return AgentPromptContext(
        agent_id=row[0],
        name=row[1] or f"Agent_{agent_id[:8]}",
        settings=settings,
        main_prompt=row[4] or "",
        mode_prompt=row[5] or "",
        personality=row[6] or "",
        scenario=row[7] or "",
        message_example=row[8] or "",
        creator_notes=row[9] or "",
        tags=list(row[10] or []),
        character_version=row[11] or "1.0",
        extensions=dict(row[12] or {}),
        intro=row[13] or "",
    )


async def get_agent_for_chat_structured(
    db: AsyncSession, agent_id: str
) -> Optional[AgentPromptContext]:
    """
    Structured, typed version of `get_agent_for_chat` for clean prompt-system callers.
    This function is intentionally not wired into production flow yet.
    """
    cached_agent_data = cache_service.get_agent_config(agent_id)
    if cached_agent_data and cached_agent_data.get("_complete_data"):
        return AgentPromptContext.from_legacy_agent_data(
            agent_id=agent_id, agent_data=cached_agent_data
        )

    try:
        query = select(
            Agent.id,
            Agent.name,
            Agent.gender,
            Agent.settings,
            Agent.main_prompt,
            Agent.mode_prompt,
            Agent.personality,
            Agent.scenario,
            Agent.message_example,
            Agent.creator_notes,
            Agent.tags,
            Agent.character_version,
            Agent.extensions,
            Agent.intro,
            Agent.avatar,
            Agent.background,
            Agent.background_animated,
            Agent.opening,
            Agent.voice_id,
            Agent.opening_audio_url,
            Agent.created_at,
            Agent.updated_at,
            Agent.version,
        ).where(and_(Agent.id == agent_id, Agent.deleted_at.is_(None)))

        result = await db.execute(query)
        row = result.first()
        if not row:
            return None

        context = _build_agent_prompt_context_from_row(agent_id, row)

        ttl = global_config.agent.agent_config_cache_ttl_seconds
        cache_service.set_agent_config(
            agent_id,
            {**context.model_dump(exclude_none=True), "_complete_data": True},
            ttl=ttl,
        )
        return context
    except SQLAlchemyError as e:
        logger.error(f"Structured agent fetch failed for {agent_id}: {e!s}")
        return None
