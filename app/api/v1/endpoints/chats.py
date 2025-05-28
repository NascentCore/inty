from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.api import deps
from app.services import chat_service

router = APIRouter()

@router.get("/", response_model=List[schemas.Chat])
def list_chats(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取聊天列表
    """
    chats = chat_service.get_chats(db, skip=skip, limit=limit)
    return chats

@router.post("/", response_model=schemas.Chat)
def create_chat(
    *,
    db: Session = Depends(deps.get_db),
    chat_in: schemas.ChatCreate,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    创建新的聊天
    """
    chat = chat_service.create_chat(db, chat_in=chat_in, user_id=current_user.id)
    return chat

@router.get("/{chat_id}", response_model=schemas.Chat)
def get_chat(
    *,
    db: Session = Depends(deps.get_db),
    chat_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    通过ID获取聊天
    """
    chat = chat_service.get_chat(db, chat_id=chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat

@router.put("/{chat_id}", response_model=schemas.Chat)
def update_chat(
    *,
    db: Session = Depends(deps.get_db),
    chat_id: str,
    chat_in: schemas.ChatUpdate,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    更新聊天
    """
    chat = chat_service.get_chat(db, chat_id=chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    chat = chat_service.update_chat(db, db_chat=chat, chat_in=chat_in)
    return chat

@router.delete("/{chat_id}", response_model=schemas.Chat)
def delete_chat(
    *,
    db: Session = Depends(deps.get_db),
    chat_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    删除聊天
    """
    chat = chat_service.get_chat(db, chat_id=chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    chat = chat_service.delete_chat(db, db_chat=chat)
    return chat 