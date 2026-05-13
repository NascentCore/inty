import logging
import uuid
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import models
from app.schemas.exclude_fields import EXCLUDE_FIELDS

from loguru import logger
from app.schemas.settings import SettingsCreate
from app.schemas.settings import SettingsUpdate


def get_settings(db: Session, user_id: str) -> Optional[models.Settings]:
    """
    获取用户设置
    """
    try:
        return (
            db.query(models.Settings).filter(models.Settings.user_id == user_id).first()
        )
    except SQLAlchemyError as e:
        logger.error(f"获取用户设置失败: {str(e)}")
        raise


def create_settings(
    db: Session, settings_in: SettingsCreate, user_id: str
) -> models.Settings:
    """
    创建新的用户设置
    """
    try:
        # 排除数据库模型中不存在的字段
        settings_data = settings_in.model_dump(exclude=EXCLUDE_FIELDS)
        db_settings = models.Settings(
            id=str(uuid.uuid4()), **settings_data, user_id=user_id
        )
        db.add(db_settings)
        db.commit()
        db.refresh(db_settings)
        return db_settings
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"创建用户设置失败: {str(e)}")
        raise


def update_settings(
    db: Session, *, db_settings: models.Settings, settings_in: SettingsUpdate
) -> models.Settings:
    """
    更新用户设置
    """
    try:
        update_data = settings_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_settings, field, value)
        db.add(db_settings)
        db.commit()
        db.refresh(db_settings)
        return db_settings
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"更新用户设置失败: {str(e)}")
        raise
