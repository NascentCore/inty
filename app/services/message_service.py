from typing import List, Optional

from sqlalchemy.orm import Session

from app import models, schemas


def get_message(db: Session, message_id: str) -> Optional[models.Message]:
    """
    通过ID获取消息
    """
    return db.query(models.Message).filter(models.Message.id == message_id).first()


def get_messages(db: Session, skip: int = 0, limit: int = 100) -> List[models.Message]:
    """
    获取消息列表
    """
    return db.query(models.Message).offset(skip).limit(limit).all()


def create_message(
    db: Session, message_in: schemas.MessageCreate, user_id: str
) -> models.Message:
    """
    创建新的消息
    """
    db_message = models.Message(**message_in.dict(), user_id=user_id)
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message


def update_message(
    db: Session, *, db_message: models.Message, message_in: schemas.MessageUpdate
) -> models.Message:
    """
    更新消息
    """
    update_data = message_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_message, field, value)
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message


def delete_message(db: Session, *, db_message: models.Message) -> models.Message:
    """
    删除消息
    """
    db.delete(db_message)
    db.commit()
    return db_message
