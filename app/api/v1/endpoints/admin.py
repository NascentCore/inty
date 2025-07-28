from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.api import deps
from app.db.session import get_async_db
from app.models.system_settings import SettingCategory
from app.schemas.response import APIResponse
from app.schemas.system_settings import (FreeUserLimitsResponse, SystemSetting,
                                         SystemSettingsListResponse,
                                         SystemSettingUpdateRequest)
from app.services.system_settings_service import system_settings_service

router = APIRouter()


async def get_current_superuser(
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> schemas.User:
    """验证当前用户是否为超级管理员"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required"
        )
    return current_user


@router.get("/system-settings", response_model=APIResponse[SystemSettingsListResponse])
async def get_all_system_settings(
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(get_current_superuser)
):
    """
    获取所有系统配置
    """
    try:
        settings = await system_settings_service.get_all_settings(db)
        
        # 转换为响应模型
        items = []
        for setting in settings:
            items.append(SystemSetting(
                key=setting.key,
                value=setting.value,
                value_type=setting.value_type,
                category=setting.category,
                description=setting.description,
                default_value=setting.default_value,
                is_system=setting.is_system,
                is_readonly=setting.is_readonly,
                updated_by=setting.updated_by,
                created_at=setting.created_at,
                updated_at=setting.updated_at,
                parsed_value=setting.parsed_value
            ))
        
        response = SystemSettingsListResponse(
            total=len(items),
            items=items
        )
        
        return APIResponse.success(data=response)
        
    except Exception as e:
        logger.error(f"获取系统配置失败: {str(e)}")
        return APIResponse.error(message="Failed to get system settings")


@router.get("/system-settings/category/{category}", response_model=APIResponse[SystemSettingsListResponse])
async def get_settings_by_category(
    category: SettingCategory,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(get_current_superuser)
):
    """
    根据分类获取系统配置
    """
    try:
        settings = await system_settings_service.get_settings_by_category(db, category)
        
        # 转换为响应模型
        items = []
        for setting in settings:
            items.append(SystemSetting(
                key=setting.key,
                value=setting.value,
                value_type=setting.value_type,
                category=setting.category,
                description=setting.description,
                default_value=setting.default_value,
                is_system=setting.is_system,
                is_readonly=setting.is_readonly,
                updated_by=setting.updated_by,
                created_at=setting.created_at,
                updated_at=setting.updated_at,
                parsed_value=setting.parsed_value
            ))
        
        response = SystemSettingsListResponse(
            total=len(items),
            items=items
        )
        
        return APIResponse.success(data=response)
        
    except Exception as e:
        logger.error(f"获取分类配置失败: {str(e)}")
        return APIResponse.error(message="Failed to get category settings")


@router.put("/system-settings/{key}", response_model=APIResponse[SystemSetting])
async def update_system_setting(
    key: str,
    request: SystemSettingUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(get_current_superuser)
):
    """
    更新系统配置
    """
    try:
        # 更新配置
        success = await system_settings_service.set_setting(
            db=db,
            key=key,
            value=request.value,
            updated_by=current_user.id
        )
        
        if not success:
            return APIResponse.error(message=f"Failed to update setting: {key}")
        
        # 获取更新后的配置
        from sqlalchemy import select

        from app.models.system_settings import SystemSettings
        
        stmt = select(SystemSettings).where(SystemSettings.key == key)
        result = await db.execute(stmt)
        setting = result.scalar_one_or_none()
        
        if not setting:
            return APIResponse.error(message=f"Setting not found: {key}")
        
        response_setting = SystemSetting(
            key=setting.key,
            value=setting.value,
            value_type=setting.value_type,
            category=setting.category,
            description=setting.description,
            default_value=setting.default_value,
            is_system=setting.is_system,
            is_readonly=setting.is_readonly,
            updated_by=setting.updated_by,
            created_at=setting.created_at,
            updated_at=setting.updated_at,
            parsed_value=setting.parsed_value
        )
        
        return APIResponse.success(data=response_setting)
        
    except Exception as e:
        logger.error(f"更新系统配置失败: {str(e)}")
        return APIResponse.error(message="Failed to update system settings")


@router.get("/system-settings/free-user-limits", response_model=APIResponse[FreeUserLimitsResponse])
async def get_free_user_limits(
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(get_current_superuser)
):
    """
    获取免费用户限制配置
    """
    try:
        limits = await system_settings_service.get_free_user_limits(db)
        
        response = FreeUserLimitsResponse(
            background_generation_limit=limits['background_generation_limit'],
            chat_total_limit=limits['chat_total_limit'],
            agent_creation_limit=limits['agent_creation_limit']
        )
        
        return APIResponse.success(data=response)
        
    except Exception as e:
        logger.error(f"获取免费用户限制失败: {str(e)}")
        return APIResponse.error(message="Failed to get free user limits")


@router.post("/system-settings/clear-cache", response_model=APIResponse[dict])
async def clear_system_settings_cache(
    key: str = None,
    current_user: schemas.User = Depends(get_current_superuser)
):
    """
    清除系统配置缓存
    """
    try:
        system_settings_service.clear_cache(key)
        
        message = f"Cache cleared for setting: {key}" if key else "All settings cache cleared"
        return APIResponse.success(
            data={"message": message},
            message=message
        )
        
    except Exception as e:
        logger.error(f"清除缓存失败: {str(e)}")
        return APIResponse.error(message="Failed to clear cache")