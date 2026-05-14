from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.api.tags import ANDROID_APP_TAG, WEB_APP_TAG
from app.api.utils.logger_route import LoggerRoute
from app.db.session import get_async_db
from app.external_services.globals import google_play_service
from app.schemas.response import APIResponse
from app.schemas.version import VersionCheckResponse, VersionReminderAction
from app.services import user_service
from app.schemas.user import User as UserSchema

router = APIRouter(prefix="/version", route_class=LoggerRoute)


@router.post(
    "/check",
    response_model=APIResponse[VersionCheckResponse],
    tags=[ANDROID_APP_TAG, WEB_APP_TAG],
)
async def check_version(
    *,
    app_version_code: int = Header(
        ..., alias="appVersionCode", description="应用版本代码"
    ),
    app_version_name: Optional[str] = Header(
        None, alias="appVersionName", description="应用版本名称（向后兼容，忽略）"
    ),
    current_user: UserSchema = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    """
    检查应用版本更新

    通过HTTP头传递版本信息：
    - appVersionCode: 应用版本代码（必填，整数），**保留给 Android 应用**；当前仅处理此头。
    - appVersionName: 应用版本名称（可选，后端会忽略，保留向后兼容）

    若未来需支持 iOS 应用，应新增独立 Header（如 iosAppVersionCode / ios_app_version_code），
    以区分 iOS 与 Android 客户端，并可按平台分别写入 users 表（如 last_ios_app_version_code）。
    """
    try:
        await user_service.update_user_last_android_app_version_code(
            db, current_user.id, app_version_code
        )
    except Exception as persist_err:
        logger.warning(
            "Failed to persist last_android_app_version_code for user %s: %s, continue anyway to check version",
            current_user.id,
            persist_err,
        )
    try:
        # 直接使用注入的版本参数
        client_version_code = app_version_code
        if app_version_name:
            logger.debug(
                "收到 appVersionName header，将忽略版本名称，仅比较 versionCode"
            )

        # 调用Google Play服务检查版本（仅基于versionCode）
        version_check_result = google_play_service.check_version_requirement(
            client_version_code
        )

        # 转换为响应模型
        response = VersionCheckResponse(**version_check_result)

        logger.debug(
            f"用户 {current_user.id} 版本检查完成: versionCode {client_version_code} -> response={response}"
        )

        return APIResponse.success(data=response)

    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"版本检查失败: {str(e)}")

        # 如果检查失败，返回保守的响应
        fallback_version_code = (
            str(app_version_code) if "app_version_code" in locals() else "unknown"
        )
        fallback_response = VersionCheckResponse(
            current_version=fallback_version_code,
            latest_version="unknown",
            update_required=False,
            force_update=False,
            minimum_version="0",
            download_url="https://play.google.com/store/apps/details?id=com.ai.inty",
            message="Version check failed",
            error=str(e),
            reminder_action=VersionReminderAction.SETTINGS_REMINDER,
        )

        return APIResponse.success(
            data=fallback_response, message="Version check failed but app can continue"
        )
