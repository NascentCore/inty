from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging
from sqlalchemy.exc import SQLAlchemyError
import traceback

from app import schemas
from app.api import deps
from app.services import get_settings, create_settings, update_settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", response_model=schemas.Settings)
def get_settings_endpoint(
    db: Session = Depends(deps.get_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取当前用户设置
    """
    try:
        logger.info(f"获取用户设置: user_id={current_user.id}")
        settings = get_settings(db, user_id=current_user.id)
        if not settings:
            logger.info(f"用户设置不存在: user_id={current_user.id}")
            raise HTTPException(status_code=404, detail="Settings not found")
        logger.info(f"成功获取用户设置: user_id={current_user.id}")
        return settings
    except SQLAlchemyError as e:
        logger.error(f"获取用户设置失败: user_id={current_user.id}, error={str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="数据库操作失败")
    except Exception as e:
        logger.error(f"获取用户设置时发生未知错误: user_id={current_user.id}, error={str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.put("/", response_model=schemas.Settings)
def update_settings_endpoint(
    *,
    db: Session = Depends(deps.get_db),
    settings_in: schemas.SettingsUpdate,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    更新当前用户设置
    """
    try:
        logger.info(f"更新用户设置: user_id={current_user.id}, settings={settings_in.dict()}")
        settings = get_settings(db, user_id=current_user.id)
        if not settings:
            # 创建新的设置
            settings_create = schemas.SettingsCreate(
                language=settings_in.language or "en",
                voice_enabled=settings_in.voice_enabled if settings_in.voice_enabled is not None else True,
                keep_talking=settings_in.keep_talking if settings_in.keep_talking is not None else True
            )
            logger.info(f"创建新用户设置: user_id={current_user.id}, settings={settings_create.dict()}")
            settings = create_settings(db, settings_in=settings_create, user_id=current_user.id)
        else:
            logger.info(f"更新现有用户设置: user_id={current_user.id}, settings={settings_in.dict()}")
            settings = update_settings(db, db_settings=settings, settings_in=settings_in)
        logger.info(f"成功更新用户设置: user_id={current_user.id}")
        return settings
    except SQLAlchemyError as e:
        logger.error(f"更新用户设置失败: user_id={current_user.id}, error={str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="数据库操作失败")
    except Exception as e:
        logger.error(f"更新用户设置时发生未知错误: user_id={current_user.id}, error={str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="服务器内部错误") 