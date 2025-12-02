"""角色主题专区 API 端点"""

import uuid
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.api import deps
from app.api.tags import INTY_EVAL_TAG, WEB_APP_TAG
from app.api.utils.logger_route import LoggerRoute
from app.schemas import character_theme as character_theme_schemas
from app.services import character_theme_service

router = APIRouter(prefix="/character-themes", route_class=LoggerRoute)


async def get_current_superuser(
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> schemas.User:
    """验证当前用户是否为超级管理员"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="只有超级用户才能访问此接口",
        )
    return current_user


@router.post(
    "/",
    response_model=schemas.APIResponse[character_theme_schemas.CharacterTheme],
    summary="创建角色主题专区",
    description="创建新的角色主题专区（需要管理员权限）",
    tags=[INTY_EVAL_TAG],
)
async def create_theme(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    theme_in: character_theme_schemas.CharacterThemeCreate,
    current_user: schemas.User = Depends(get_current_superuser),
) -> Any:
    """创建角色主题专区"""
    try:
        theme = await character_theme_service.create_theme(db, theme_in)
        theme_schema = character_theme_schemas.CharacterTheme.model_validate(theme)
        return schemas.APIResponse.success(data=theme_schema)
    except Exception as e:
        logger.error(f"创建角色主题专区失败: {str(e)}")
        return schemas.APIResponse.error(message=f"创建专区失败: {str(e)}")


@router.get(
    "/",
    response_model=schemas.APIResponse[List[character_theme_schemas.CharacterTheme]],
    summary="获取角色主题专区列表",
    description="获取所有角色主题专区列表（所有已认证用户可访问）",
    tags=[INTY_EVAL_TAG, WEB_APP_TAG],
)
async def list_themes(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的记录数"),
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """获取角色主题专区列表"""
    try:
        themes = await character_theme_service.list_themes(db, skip=skip, limit=limit)
        theme_schemas = [
            character_theme_schemas.CharacterTheme.model_validate(theme)
            for theme in themes
        ]
        return schemas.APIResponse.success(data=theme_schemas)
    except Exception as e:
        logger.error(f"获取角色主题专区列表失败: {str(e)}")
        return schemas.APIResponse.error(message=f"获取专区列表失败: {str(e)}")


@router.get(
    "/{theme_id}",
    response_model=schemas.APIResponse[character_theme_schemas.CharacterTheme],
    summary="获取角色主题专区详情",
    description="获取指定角色主题专区的详细信息（所有已认证用户可访问）",
    tags=[INTY_EVAL_TAG, WEB_APP_TAG],
)
async def get_theme(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    theme_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """获取角色主题专区详情"""
    try:
        theme = await character_theme_service.get_theme(db, theme_id)
        if not theme:
            return schemas.APIResponse.error(message="专区不存在", code=404)
        theme_schema = character_theme_schemas.CharacterTheme.model_validate(theme)
        return schemas.APIResponse.success(data=theme_schema)
    except Exception as e:
        logger.error(f"获取角色主题专区详情失败: {str(e)}")
        return schemas.APIResponse.error(message=f"获取专区详情失败: {str(e)}")


@router.put(
    "/{theme_id}",
    response_model=schemas.APIResponse[character_theme_schemas.CharacterTheme],
    summary="更新角色主题专区",
    description="更新角色主题专区信息（需要管理员权限）",
    tags=[INTY_EVAL_TAG],
)
async def update_theme(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    theme_id: str,
    theme_in: character_theme_schemas.CharacterThemeUpdate,
    current_user: schemas.User = Depends(get_current_superuser),
) -> Any:
    """更新角色主题专区"""
    try:
        theme = await character_theme_service.update_theme(db, theme_id, theme_in)
        if not theme:
            return schemas.APIResponse.error(message="专区不存在", code=404)
        theme_schema = character_theme_schemas.CharacterTheme.model_validate(theme)
        return schemas.APIResponse.success(data=theme_schema)
    except Exception as e:
        logger.error(f"更新角色主题专区失败: {str(e)}")
        return schemas.APIResponse.error(message=f"更新专区失败: {str(e)}")


@router.delete(
    "/{theme_id}",
    response_model=schemas.APIResponse[dict],
    summary="删除角色主题专区",
    description="删除角色主题专区（需要管理员权限）",
    tags=[INTY_EVAL_TAG],
)
async def delete_theme(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    theme_id: str,
    current_user: schemas.User = Depends(get_current_superuser),
) -> Any:
    """删除角色主题专区"""
    try:
        success = await character_theme_service.delete_theme(db, theme_id)
        if not success:
            return schemas.APIResponse.error(message="专区不存在", code=404)
        return schemas.APIResponse.success(data={"message": "专区删除成功"})
    except Exception as e:
        logger.error(f"删除角色主题专区失败: {str(e)}")
        return schemas.APIResponse.error(message=f"删除专区失败: {str(e)}")


@router.post(
    "/{theme_id}/agents",
    response_model=schemas.APIResponse[character_theme_schemas.CharacterThemeAgent],
    summary="添加角色到专区",
    description="向指定专区添加角色（需要管理员权限）",
    tags=[INTY_EVAL_TAG],
)
async def add_agent_to_theme(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    theme_id: str,
    request: character_theme_schemas.AddAgentToThemeRequest,
    current_user: schemas.User = Depends(get_current_superuser),
) -> Any:
    """添加角色到专区"""
    try:
        theme_agent = await character_theme_service.add_agent_to_theme(
            db, theme_id, request.agent_id
        )
        theme_agent_schema = character_theme_schemas.CharacterThemeAgent.model_validate(
            theme_agent
        )
        return schemas.APIResponse.success(data=theme_agent_schema)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加角色到专区失败: {str(e)}")
        return schemas.APIResponse.error(message=f"添加角色失败: {str(e)}")


@router.delete(
    "/{theme_id}/agents/{agent_id}",
    response_model=schemas.APIResponse[dict],
    summary="从专区移除角色",
    description="从指定专区移除角色（需要管理员权限）",
    tags=[INTY_EVAL_TAG],
)
async def remove_agent_from_theme(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    theme_id: str,
    agent_id: str,
    current_user: schemas.User = Depends(get_current_superuser),
) -> Any:
    """从专区移除角色"""
    try:
        success = await character_theme_service.remove_agent_from_theme(
            db, theme_id, agent_id
        )
        if not success:
            return schemas.APIResponse.error(
                message="专区或角色不存在，或角色不在该专区中", code=404
            )
        return schemas.APIResponse.success(data={"message": "角色移除成功"})
    except Exception as e:
        logger.error(f"从专区移除角色失败: {str(e)}")
        return schemas.APIResponse.error(message=f"移除角色失败: {str(e)}")


@router.put(
    "/{theme_id}/agents/reorder",
    response_model=schemas.APIResponse[dict],
    summary="调整角色顺序",
    description="调整专区中角色的顺序（需要管理员权限）",
    tags=[INTY_EVAL_TAG],
)
async def reorder_agents(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    theme_id: str,
    request: character_theme_schemas.ReorderAgentsRequest,
    current_user: schemas.User = Depends(get_current_superuser),
) -> Any:
    """调整角色顺序"""
    try:
        await character_theme_service.reorder_agents(db, theme_id, request.agent_ids)
        return schemas.APIResponse.success(data={"message": "角色顺序调整成功"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"调整角色顺序失败: {str(e)}")
        return schemas.APIResponse.error(message=f"调整顺序失败: {str(e)}")
