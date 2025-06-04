from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas

async def get_agent(db: AsyncSession, agent_id: str) -> Optional[models.Agent]:
    """
    通过ID获取AI角色
    """
    result = await db.execute(
        select(models.Agent)
        .where(models.Agent.id == agent_id)
    )
    return result.scalar_one_or_none()

async def get_agents(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[models.Agent]:
    """
    获取AI角色列表
    """
    result = await db.execute(
        select(models.Agent)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def create_agent(db: AsyncSession, agent_in: schemas.AgentCreate, user_id: str) -> models.Agent:
    """
    创建新的AI角色
    """
    db_agent = models.Agent(**agent_in.dict(), user_id=user_id)
    db.add(db_agent)
    await db.commit()
    await db.refresh(db_agent)
    return db_agent

async def update_agent(db: AsyncSession, db_agent: models.Agent, agent_in: schemas.AgentUpdate) -> models.Agent:
    """
    更新AI角色
    """
    for field, value in agent_in.dict(exclude_unset=True).items():
        setattr(db_agent, field, value)
    await db.commit()
    await db.refresh(db_agent)
    return db_agent

async def delete_agent(db: AsyncSession, db_agent: models.Agent) -> models.Agent:
    """
    删除AI角色
    """
    await db.delete(db_agent)
    await db.commit()
    return db_agent 