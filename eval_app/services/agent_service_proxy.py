# CREATED_BY_AGENT
"""
Agent 服务代理 - 直接调用主应用的服务层
"""

from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.services import agent_service


async def get_user_agents(
    db: AsyncSession,
    current_user: schemas.User,
    skip: int = 0,
    limit: int = 100,
) -> List[schemas.Agent]:
    """获取用户的智能体列表"""
    return await agent_service.get_user_agents(
        db, current_user=current_user, skip=skip, limit=limit
    )


async def get_agent(db: AsyncSession, agent_id: str) -> Optional[schemas.Agent]:
    """获取智能体详情"""
    return await agent_service.get_agent(db, agent_id=agent_id)


async def get_recommended_agents(
    db: AsyncSession, skip: int = 0, limit: int = 20
) -> List[schemas.Agent]:
    """获取推荐智能体"""
    return await agent_service.get_recommended_agents(db, skip=skip, limit=limit)


async def search_agents(
    db: AsyncSession,
    query: str,
    page: int = 1,
    page_size: int = 10,
) -> schemas.PaginationData[schemas.Agent]:
    """搜索智能体"""
    return await agent_service.search_agents(
        db, query=query, page=page, page_size=page_size
    )


async def create_agent(
    db: AsyncSession,
    agent_in: schemas.AgentCreate,
    creator_id: str,
) -> schemas.Agent:
    """创建智能体"""
    return await agent_service.create_agent(
        db=db, agent_in=agent_in, creator_id=creator_id
    )


async def update_agent(
    db: AsyncSession,
    agent_id: str,
    agent_in: schemas.AgentUpdate,
) -> schemas.Agent:
    """更新智能体"""
    return await agent_service.update_agent(
        db=db, agent_id=agent_id, agent_in=agent_in
    )


async def delete_agent(db: AsyncSession, agent_id: str) -> None:
    """删除智能体"""
    await agent_service.delete_agent(db=db, agent_id=agent_id)


async def get_agent_for_chat(
    db: AsyncSession, agent_id: str
) -> Optional[dict]:
    """获取用于聊天的智能体数据"""
    return await agent_service.get_agent_for_chat(db, agent_id)

