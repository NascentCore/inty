from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.api import deps
from app.services import message_service

router = APIRouter()

@router.get("/", response_model=List[schemas.Message])
def list_messages(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取消息列表
    """
    messages = message_service.get_messages(db, skip=skip, limit=limit)
    return messages

@router.post("/", response_model=schemas.Message)
def create_message(
    *,
    db: Session = Depends(deps.get_db),
    message_in: schemas.MessageCreate,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    创建新的消息
    """
    message = message_service.create_message(db, message_in=message_in, user_id=current_user.id)
    return message

@router.get("/{message_id}", response_model=schemas.Message)
def get_message(
    *,
    db: Session = Depends(deps.get_db),
    message_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    通过ID获取消息
    """
    message = message_service.get_message(db, message_id=message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    return message

@router.put("/{message_id}", response_model=schemas.Message)
def update_message(
    *,
    db: Session = Depends(deps.get_db),
    message_id: str,
    message_in: schemas.MessageUpdate,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    更新消息
    """
    message = message_service.get_message(db, message_id=message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    message = message_service.update_message(db, db_message=message, message_in=message_in)
    return message

@router.delete("/{message_id}", response_model=schemas.Message)
def delete_message(
    *,
    db: Session = Depends(deps.get_db),
    message_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    删除消息
    """
    message = message_service.get_message(db, message_id=message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    message = message_service.delete_message(db, db_message=message)
    return message 