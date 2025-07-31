import logging
import uuid
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import models, schemas

logger = logging.getLogger(__name__)


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
    db: Session, settings_in: schemas.SettingsCreate, user_id: str
) -> models.Settings:
    """
    创建新的用户设置
    """
    try:
        db_settings = models.Settings(
            id=str(uuid.uuid4()), **settings_in.dict(), user_id=user_id
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
    db: Session, *, db_settings: models.Settings, settings_in: schemas.SettingsUpdate
) -> models.Settings:
    """
    更新用户设置
    """
    try:
        update_data = settings_in.dict(exclude_unset=True)
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
