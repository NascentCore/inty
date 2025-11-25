"""
V2 AI Agent related endpoints.
"""

# CREATED_BY_AGENT

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.api import deps
from app.api.utils.logger_route import LoggerRoute
from app.services import agent_service

router = APIRouter(prefix="/ai/agents", route_class=LoggerRoute)


@router.get(
    "/recommend",
    response_model=schemas.AgentRecommendationResponse,
    summary="获取推荐 AI 角色列表（v2）",
    description=(
        "返回公开且审核通过的 AI 角色列表，支持按创建时间、随机或基于评分的随机排序。"
        "若 sort 为 random 或 score_based_random，需要提供 sort_seed 以保证返回顺序稳定。"
    ),
)
async def recommend_agents_v2(
    request: schemas.AgentRecommendationRequest = Depends(),
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> schemas.AgentRecommendationResponse:
    pagination_data = await agent_service.get_recommended_agents_paginated(
        db,
        current_user=current_user,
        page=request.page,
        page_size=request.page_size,
        sort_by=request.sort,
        sort_seed=request.sort_seed,
    )
    return schemas.AgentRecommendationResponse.success(data=pagination_data)
