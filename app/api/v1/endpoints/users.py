from typing import Any
import traceback
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.schemas.response import APIResponse
from app.schemas.user import User, UserUpdate, DeviceTokenRegister
from app.api import deps
from app.db.session import get_async_db
from app.services import user_service
from app.utils.gcs import upload_to_gcs, delete_from_gcs
from app.core.config import settings

router = APIRouter()

@router.get("/profile", response_model=User)
def get_profile(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user profile.
    """
    return current_user

@router.put("/profile", response_model=User)
async def update_profile(
    *,
    db: AsyncSession = Depends(get_async_db),
    user_in: UserUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update current user profile.
    """
    try:
        user = await user_service.update_user(db, current_user.id, user_in)
        return user
    except Exception as e:
        logger.error(f"更新用户信息失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/avatar", response_model=APIResponse[User])
async def upload_avatar(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    try:
        file_data = await file.read()
        avatar_path = user_service.generate_avatar_path(current_user.id, file.filename)
        url = upload_to_gcs(file_data, file.content_type, settings.gcs.bucket, avatar_path)
        # 删除旧头像
        old_avatar = current_user.avatar
        if old_avatar:
            old_path = user_service.get_path_from_gcs_url(old_avatar)
            if old_path:
                delete_from_gcs(settings.gcs.bucket, old_path)
        user = await user_service.update_user(db, current_user.id, UserUpdate(avatar=url))
        return APIResponse.success(data=user)
    except Exception as e:
        logger.error(f"头像上传失败: {str(e)}")
        return APIResponse.error(message=str(e))

@router.post("/device/register", response_model=APIResponse)
async def register_device_token(
    device_in: DeviceTokenRegister,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    注册或更新设备token
    """
    try:
        device_token = await user_service.register_device_token(
            db=db,
            token=device_in.token,
            user_id=current_user.id
        )
        return APIResponse.success(message="设备token注册成功")
    except Exception as e:
        logger.error(f"注册设备token失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return APIResponse.error(message=str(e))

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

