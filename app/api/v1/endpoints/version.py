import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Header

from app import schemas
from app.api import deps
from app.api.utils.logger_route import LoggerRoute
from app.schemas.response import APIResponse
from app.schemas.version import VersionCheckResponse
from app.services.google_play_service import google_play_service

router = APIRouter(prefix="/version", route_class=LoggerRoute)
logger = logging.getLogger(__name__)


@router.post("/check", response_model=APIResponse[VersionCheckResponse])
async def check_version(
    *,
    app_version_code: int = Header(
        ..., alias="appVersionCode", description="应用版本代码"
    ),
    app_version_name: Optional[str] = Header(
        None, alias="appVersionName", description="应用版本名称（可选）"
    ),
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    检查应用版本更新

    通过HTTP头传递版本信息：
    - appVersionCode: 应用版本代码（必填，整数）
    - appVersionName: 应用版本名称（可选，字符串）
    """
    try:
        # 直接使用注入的版本参数
        client_version_code = app_version_code
        version_name = app_version_name or "unknown"

        # 调用Google Play服务检查版本
        version_check_result = google_play_service.check_version_requirement(
            client_version_code
        )

        # 转换为响应模型
        response = VersionCheckResponse(**version_check_result)

        logger.info(
            f"用户 {current_user.id} 版本检查完成: versionCode {client_version_code} "
            f"(versionName: {version_name}) -> "
            f"需要更新: {response.update_required}, 强制更新: {response.force_update}"
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
            download_url=f"https://play.google.com/store/apps/details?id=com.ai.inty",
            message="Version check failed",
            error=str(e),
        )

        return APIResponse.success(
            data=fallback_response, message="Version check failed but app can continue"
        )
