import traceback
from typing import Any, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
)
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.config import settings
from app.db.session import get_async_db
from app.schemas.response import APIResponse
from app.schemas.user import DeviceTokenRegister, User, UserList, UserUpdate
from app.schemas.user_deletion import (
    AccountDeletionRequest,
    AccountDeletionResponse,
    AnonymizationStatsResponse,
    DeletionCheckResponse,
)
from app.services import user_service
from app.utils.gcs import delete_from_gcs, is_user_gcs_file, upload_to_gcs

router = APIRouter()


@router.get("/profile", response_model=User)
async def get_profile(
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    """
    Get current user profile.
    """
    # 计算connector_count
    connector_count = await user_service.get_user_connector_count(db, current_user.id)

    # 创建用户响应对象，包含connector_count
    user_dict = {
        "id": current_user.id,
        "readable_id": current_user.readable_id,
        "nickname": current_user.nickname,
        "avatar": current_user.avatar,
        "email": current_user.email,
        "phone": current_user.phone,
        "gender": current_user.gender,
        "age_group": current_user.age_group,
        "description": current_user.description,
        "system_language": current_user.system_language,
        "auth_type": current_user.auth_type,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at,
        "is_superuser": current_user.is_superuser,
        "public_agents_count": 0,  # 这些字段可能需要其他查询来获取
        "total_public_agents_follows": 0,
        "followers_count": 0,
        "connector_count": connector_count,
    }

    return User(**user_dict)


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
    current_user: User = Depends(deps.get_current_active_user),
):
    try:
        file_data = await file.read()
        avatar_path = user_service.generate_avatar_path(current_user.id, file.filename)
        url = upload_to_gcs(
            file_data, file.content_type, settings.gcs.bucket, avatar_path
        )

        # 删除旧头像，但只有当它确实是存储在用户GCS bucket中的文件时才删除
        old_avatar = current_user.avatar
        if old_avatar and is_user_gcs_file(old_avatar, settings.gcs.bucket):
            old_path = user_service.get_path_from_gcs_url(old_avatar)
            if old_path:
                delete_from_gcs(settings.gcs.bucket, old_path)
                logger.info(f"已删除旧头像: {old_avatar}")
        elif old_avatar:
            logger.info(f"跳过删除非GCS头像: {old_avatar}")

        user = await user_service.update_user(
            db, current_user.id, UserUpdate(avatar=url)
        )
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
            db=db, token=device_in.token, user_id=current_user.id
        )
        return APIResponse.success(message="Device token registered successfully")
    except Exception as e:
        logger.error(f"注册设备token失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return APIResponse.error(message=str(e))


@router.get("/deletion/check", response_model=APIResponse[DeletionCheckResponse])
async def check_deletion_eligibility(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    检查用户是否可以删除账户
    """
    try:
        can_delete, error_message = await user_service.check_user_can_delete_account(
            db, current_user.id
        )

        response_data = DeletionCheckResponse(
            can_delete=can_delete,
            error_message=error_message if not can_delete else None,
            active_subscription=not can_delete and "订阅" in (error_message or ""),
        )

        return APIResponse.success(data=response_data)

    except Exception as e:
        logger.error(f"检查删除权限失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return APIResponse.error(message="Failed to check deletion permissions")


@router.post("/delete-account", response_model=APIResponse[AccountDeletionResponse])
async def delete_user_account(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(deps.get_current_active_user),
    request: Optional[AccountDeletionRequest] = None,
) -> Any:
    """
    删除用户账户
    """
    try:
        # 执行账户删除
        deletion_reason = "用户主动删除"
        if request and request.reason:
            deletion_reason = request.reason

        deletion_result = await user_service.delete_user_account(
            db=db,
            user_id=current_user.id,
            deletion_reason=deletion_reason,
            processor_id=current_user.id,
        )

        if not deletion_result["success"]:
            return APIResponse.error(message=deletion_result["message"])

        # 异步执行相关数据匿名化
        background_tasks.add_task(
            user_service.anonymize_related_data, db, current_user.id
        )

        response_data = AccountDeletionResponse(
            success=deletion_result["success"],
            message=deletion_result["message"],
            user_id=deletion_result["user_id"],
            deletion_log_id=deletion_result.get("deletion_log_id"),
            anonymized_fields=deletion_result.get("anonymized_fields"),
        )

        return APIResponse.success(data=response_data)

    except Exception as e:
        logger.error(f"删除用户账户失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return APIResponse.error(
            message="Account deletion failed, please try again later"
        )


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


@router.get("/", response_model=UserList)
async def get_all_users(
    *,
    db: AsyncSession = Depends(get_async_db),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(50, ge=1, le=100, description="每页记录数"),
    search: Optional[str] = Query(
        None, description="搜索关键字，可匹配昵称和readable_id"
    ),
) -> Any:
    """
    获取所有用户信息，支持分页和关键字搜索
    """
    try:
        logger.info(f"获取所有用户 - skip: {skip}, limit: {limit}, search: {search}")

        # 调用service层方法获取所有用户
        result = await user_service.get_all_users(
            db=db, skip=skip, limit=limit, search=search
        )

        logger.info(
            f"用户列表查询完成 - 总记录数: {result['total']}, "
            f"当前页记录数: {len(result['items'])}"
        )

        return UserList(**result)

    except Exception as e:
        logger.error(f"获取所有用户失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get user list: {str(e)}"
        )
