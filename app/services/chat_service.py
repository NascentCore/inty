from typing import List, Optional
from sqlalchemy.orm import Session

from app import models, schemas

def get_chat(db: Session, chat_id: str) -> Optional[models.Chat]:
    """
    通过ID获取聊天
    """
    return db.query(models.Chat).filter(models.Chat.id == chat_id).first()

def get_chats(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.Chat]:
    """
    获取聊天列表
    """
    return db.query(models.Chat).offset(skip).limit(limit).all()

def create_chat(
    db: Session, chat_in: schemas.ChatCreate, user_id: str
) -> models.Chat:
    """
    创建新的聊天
    """
    db_chat = models.Chat(
        **chat_in.dict(),
        user_id=user_id
    )
    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)
    return db_chat

def update_chat(
    db: Session,
    *,
    db_chat: models.Chat,
    chat_in: schemas.ChatUpdate
) -> models.Chat:
    """
    更新聊天
    """
    update_data = chat_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_chat, field, value)
    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)
    return db_chat

def delete_chat(
    db: Session,
    *,
    db_chat: models.Chat
) -> models.Chat:
    """
    删除聊天
    """
    db.delete(db_chat)
    db.commit()
    return db_chat 