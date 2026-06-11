from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio.session import AsyncSession

from app.models.agent import Agent


async def _agent_status_line_for_chat_header(
    db: AsyncSession, agent_id: str
) -> Optional[str]:
    r = await db.execute(
        select(Agent.status_line).where(
            Agent.id == agent_id,
            Agent.deleted_at.is_(None),
        )
    )
    raw = r.scalar_one_or_none()
    text = (raw or "").strip()
    return text if text else None
