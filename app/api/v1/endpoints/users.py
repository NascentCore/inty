import traceback
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.api.tags import (
    ANDROID_APP_TAG,
    EVALUATION_APP_TAG,
    NOT_USED_TAG,
    WEB_APP_TAG,
)
from app.api.utils.logger_route import LoggerRoute
from app.db.session import get_async_db
from app.schemas.response import APIResponse
from app.schemas.user import DeviceTokenRegister, User, UserList, UserUpdate
from app.schemas.user_deletion import (
    AccountDeletionRequest,
    AccountDeletionResponse,
    DeletionCheckResponse,
)
from app.services import user_action_service, user_service
from app.services.global_services import subscription_service

router = APIRouter(prefix="/users", route_class=LoggerRoute)


@router.get(
    "/profile",
    deprecated=True,
    include_in_schema=False,
    summary="[Deprecated, use /me, kept for v1.0.3 compatibility]",
    response_model=User,
    tags=[ANDROID_APP_TAG],
)
async def get_profile(
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    """
    Get current user profile.
    """
    # 计算connector_count
    connector_count = await user_service.get_user_connector_count(
        db, current_user.id
    )

    # 创建用户响应对象，包含connector_count
    user_dict = {
        "id": current_user.id,
        # DEPRECATED: app 显示 ID 而非 readable_id
        "readable_id": current_user.readable_id,
        "nickname": current_user.nickname,
        "avatar": current_user.avatar,
        "email": current_user.email,
        "user_photo": current_user.user_photo,
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


@router.get(
    "/me",
    response_model=APIResponse[User],
    tags=[ANDROID_APP_TAG, WEB_APP_TAG],
)
async def get_me(
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    """
    Get current user profile.
    """
    connector_count = await user_service.get_user_connector_count(
        db, current_user.id
    )
    actions = await user_action_service.get_user_actions(db, current_user.id)

    user_dict = {
        "id": current_user.id,
        # DEPRECATED: app 显示 ID 而非 readable_id
        "readable_id": current_user.readable_id,
        "nickname": current_user.nickname,
        "avatar": current_user.avatar,
        "email": current_user.email,
        "user_photo": current_user.user_photo,
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
        "public_agents_count": 0,
        "total_public_agents_follows": 0,
        "followers_count": 0,
        "connector_count": connector_count,
        "actions": actions,
    }

    return APIResponse.success(data=User(**user_dict))


# TODO: 考虑路径更改为 /me 这样与 GET /me 一致。GET /me 最早改动是为了兼容 v1.0.3 的 API。
# 可能这个 api 也有同样的问题。需要考虑 1.0.3 tag inty-app 里是否与这个 API 兼容。
@router.put(
    "/profile",
    response_model=APIResponse[User],
    summary="Update current user profile",
    description="Update current user profile, support avatar update",
    tags=[ANDROID_APP_TAG, WEB_APP_TAG],
)
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
        return APIResponse.success(data=user)
    except Exception as e:
        logger.error(f"更新用户信息失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return APIResponse.error(message=str(e))


# TODO: https://github.com/NascentCore/inty/issues/771
# 基于设备推送实现主动发消息
# TODO：考虑将改 API 合并到另一个已有的 API，比如用户登录 API，直接注册对应的 device ID，
# 以此来减少 endpoint 数量
@router.post(
    "/device/register",
    response_model=APIResponse,
    include_in_schema=False,
    summary="Registers or updates Firebase Cloud Messaging (FCM) device tokens for push notifications",
    description="在用户未打开 app 时向设备推送消息",
    tags=[ANDROID_APP_TAG],
)
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
        return APIResponse.success(
            message="Device token registered successfully"
        )
    except Exception as e:
        logger.error(f"注册设备token失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return APIResponse.error(message=str(e))


@router.get(
    "/deletion/check",
    response_model=APIResponse[DeletionCheckResponse],
    tags=[ANDROID_APP_TAG, WEB_APP_TAG, NOT_USED_TAG],
    deprecated=True,
    summary="DEPRECATED: POST /api/v1/users/delete-account 已经做了此检查",
)
async def check_deletion_eligibility(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    检查用户是否可以删除账户

    .. deprecated::
        此端点已废弃，请使用 POST /api/v1/users/delete-account 端点。
        删除账户时会自动执行相同的检查。
    """
    try:
        can_delete, error_message = (
            await user_service.check_user_can_delete_account(
                db, current_user.id
            )
        )

        response_data = DeletionCheckResponse(
            can_delete=can_delete,
            error_message=error_message if not can_delete else None,
            active_subscription=not can_delete
            and "订阅" in (error_message or ""),
        )

        return APIResponse.success(data=response_data)

    except Exception as e:
        logger.error(f"检查删除权限失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return APIResponse.error(message="Failed to check deletion permissions")


@router.post(
    "/delete-account",
    response_model=APIResponse[AccountDeletionResponse],
    tags=[ANDROID_APP_TAG, WEB_APP_TAG, NOT_USED_TAG],
)
async def delete_user_account(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(deps.get_current_user),
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
            subscription_service=subscription_service,
            deletion_reason=deletion_reason,
        )

        if not deletion_result["success"]:
            return APIResponse.error(message=deletion_result["message"])

        response_data = AccountDeletionResponse(
            success=deletion_result["success"],
            message=deletion_result["message"],
            user_id=deletion_result["user_id"],
        )

        return APIResponse.success(data=response_data)

    except Exception as e:
        logger.error(f"删除用户账户失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return APIResponse.error(
            message="Account deletion failed, please try again later"
        )


# TODO: Move this to admin router, and do not include the router in production.
@router.get(
    "",
    response_model=UserList,
    include_in_schema=False,
    tags=[EVALUATION_APP_TAG, NOT_USED_TAG],
)
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
        logger.debug(
            f"获取所有用户 - skip: {skip}, limit: {limit}, search: {search}"
        )

        # 调用service层方法获取所有用户
        result = await user_service.get_all_users(
            db=db, skip=skip, limit=limit, search=search
        )

        logger.debug(
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
