from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.api import deps
from app.services import agent_service

router = APIRouter()

@router.get("/", response_model=List[schemas.Agent])
async def list_agents(
    db: AsyncSession = Depends(deps.get_async_db),
    skip: int = 0,
    limit: int = 100,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取当前用户创建的AI角色列表
    """
    agents = await agent_service.get_user_agents(db, user_id=current_user.id, skip=skip, limit=limit)
    return agents

@router.get("/recommend", response_model=schemas.APIResponse[schemas.PaginationData[schemas.Agent]])
async def recommend_agents(
    db: AsyncSession = Depends(deps.get_async_db),
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量，最大100"),
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取推荐的AI角色列表（公开且已审核的角色，按创建时间倒序）
    """
    pagination_data = await agent_service.get_recommended_agents_paginated(db, page=page, page_size=page_size)
    return schemas.APIResponse.success(data=pagination_data)

@router.post("/", response_model=schemas.Agent)
async def create_agent(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_in: schemas.AgentCreate,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    创建新的AI角色
    """
    agent = await agent_service.create_agent(db, agent_in=agent_in, user_id=current_user.id)
    return agent

@router.get("/{agent_id}", response_model=schemas.Agent)
async def get_agent(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    通过ID获取AI角色
    """
    agent = await agent_service.get_agent(db, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.put("/{agent_id}", response_model=schemas.Agent)
async def update_agent(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    agent_in: schemas.AgentUpdate,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    更新AI角色
    """
    agent = await agent_service.get_agent(db, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent = await agent_service.update_agent(db, db_agent=agent, agent_in=agent_in)
    return agent

@router.delete("/{agent_id}", response_model=schemas.Agent)
async def delete_agent(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    删除AI角色
    """
    agent = await agent_service.get_agent(db, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent = await agent_service.delete_agent(db, db_agent=agent)
    return agent 