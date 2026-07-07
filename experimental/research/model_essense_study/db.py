from __future__ import annotations

import hashlib
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent, AgentVisibility, AgentStatus
from app.models.chat_history import ChatHistory
from app.models.user import Gender
from research.model_essense_study.schema import AgentPersonaRaw, StimulusCandidateRecord


def _extract_chat_message_text(message: object) -> Optional[str]:
    if not isinstance(message, dict):
        return None
    data = message.get("data")
    if isinstance(data, dict):
        content = data.get("content")
        if isinstance(content, str):
            return content
    content = message.get("content")
    if isinstance(content, str):
        return content
    return None


def _agent_to_raw(agent: Agent) -> AgentPersonaRaw:
    tags = agent.tags if isinstance(agent.tags, list) else []
    normalized_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
    gender_value = (
        agent.gender.value
        if isinstance(agent.gender, Gender)
        else str(agent.gender) if agent.gender else "OTHER"
    )
    return AgentPersonaRaw(
        agent_id=agent.id,
        name=agent.name,
        gender=gender_value,
        personality=(agent.personality or "").strip(),
        scenario=(agent.scenario or "").strip(),
        tags=normalized_tags,
        meta_data=agent.meta_data if isinstance(agent.meta_data, dict) else {},
    )


async def load_persona_raw_agents(
    db: AsyncSession,
    *,
    limit: int,
) -> list[AgentPersonaRaw]:
    rows = await db.execute(
        select(Agent)
        .where(
            and_(
                Agent.deleted_at.is_(None),
                Agent.visibility == AgentVisibility.PUBLIC,
                Agent.status == AgentStatus.APPROVED,
            )
        )
        .order_by(Agent.created_at.desc())
        .limit(limit)
    )
    agents = rows.scalars().all()
    return [_agent_to_raw(agent) for agent in agents]


async def load_stimulus_candidates(
    db: AsyncSession,
    *,
    query_limit: int,
) -> list[StimulusCandidateRecord]:
    rows = await db.execute(
        select(
            ChatHistory.id,
            ChatHistory.session_id,
            ChatHistory.message,
            ChatHistory.created_at,
        )
        .where(ChatHistory.deleted_at.is_(None))
        .order_by(ChatHistory.created_at.desc())
        .limit(query_limit)
    )
    records: list[StimulusCandidateRecord] = []
    for row in rows:
        message_obj = row.message if isinstance(row.message, dict) else {}
        message_type = message_obj.get("type")
        if message_type not in ("human", "HumanMessage"):
            continue
        raw_text = _extract_chat_message_text(message_obj)
        if not raw_text:
            continue
        source_hash = hashlib.sha256(
            f"{row.session_id}:{row.id}".encode("utf-8")
        ).hexdigest()[:16]
        records.append(
            StimulusCandidateRecord(
                candidate_id=f"chatmsg:{row.id}",
                text=raw_text,
                source_chat_message_id=row.id,
                source_session_id_hash=source_hash,
                created_at=row.created_at.isoformat() if row.created_at else None,
            )
        )
    return records
