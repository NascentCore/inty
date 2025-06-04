from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.api import deps
from app.db.session import get_async_db
from app.services import user_service

router = APIRouter()

# @router.get("/profile", response_model=schemas.User)
# def get_profile(
#     current_user: schemas.User = Depends(deps.get_current_active_user),
# ) -> Any:
#     """
#     Get current user profile.
#     """
#     return current_user

# @router.put("/profile", response_model=schemas.User)
# def update_profile(
#     *,
#     db: AsyncSession = Depends(get_async_db),
#     user_in: schemas.UserUpdate,
#     current_user: schemas.User = Depends(deps.get_current_active_user),
# ) -> Any:
#     """
#     Update current user profile.
#     """
#     # TODO: 实现用户信息更新
#     raise NotImplementedError("Update profile not implemented yet")

# @router.get("/{user_id}/profile", response_model=schemas.User)
# def get_user_profile(
#     user_id: str,
#     db: AsyncSession = Depends(get_async_db),
#     current_user: schemas.User = Depends(deps.get_current_active_user),
# ) -> Any:
#     """
#     Get user profile by ID.
#     """
#     user = await user_service.get_user(db, user_id)
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#     return user 