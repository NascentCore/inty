"""Persist companion-visible agent status_line (chat header subtitle)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from loguru import logger
from sqlalchemy import select

from app import models, schemas
from app.db.session import AsyncSessionLocal
from app.services import agent_service


def agent_id_from_companion_workspace_root(root: Path) -> str:
    """Workspace root is ``.../<user_id>/<agent_id>/<chat_id>``; agent id is parent of chat folder."""
    return root.resolve().parent.name


async def persist_agent_status_line(agent_id: str, status_line: Optional[str]) -> None:
    """Writes ``agents.status_line``. Empty or whitespace clears the column."""
    normalized = (status_line or "").strip()
    payload = normalized if normalized else None
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(models.Agent).where(
                models.Agent.id == agent_id,
                models.Agent.deleted_at.is_(None),
            )
        )
        agent = result.scalar_one_or_none()
        if agent is None:
            logger.warning(
                "persist_agent_status_line skipped: agent not found agent_id={}",
                agent_id,
            )
            return
        await agent_service.update_agent(
            db,
            agent,
            schemas.AgentUpdate(status_line=payload),
        )


async def tool_update_agent_status_line(root: Path, status_line: str) -> str:
    """Companion tool: set short chat-header status line for this agent."""
    agent_id = agent_id_from_companion_workspace_root(root)
    await persist_agent_status_line(agent_id, status_line)
    return "OK updated agent status line"
