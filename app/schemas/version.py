from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class VersionReminderAction(str, Enum):
    """客户端需要展示的提醒类型"""

    # 不进行任何提醒
    NONE = "NONE"

    # 显示设置提醒
    SETTINGS_REMINDER = "SETTINGS_REMINDER"

    # 显示弹窗提醒
    POP_UP_REMINDER = "POP_UP_REMINDER"

    # 强制拦截继续使用
    BLOCK_ACCESS = "BLOCK_ACCESS"


class VersionCheckRequest(BaseModel):
    """版本检查请求模型"""

    version: str = Field(..., description="客户端版本代码", example="123")
    platform: str = Field(
        default="android", description="平台类型", example="android"
    )
    request_id: Optional[str] = None


class VersionCheckResponse(BaseModel):
    """版本检查响应模型"""

    reminder_action: VersionReminderAction = Field(
        default=VersionReminderAction.NONE,
        description="客户端需要展示的提醒动作，None 表示无需额外提醒",
    )
    current_version: Optional[str] = Field(None, description="当前客户端版本")
    latest_version: Optional[str] = Field(None, description="最新可用版本")
    latest_version_code: Optional[int] = Field(None, description="最新版本代码")
    update_required: Optional[bool] = Field(None, description="是否需要更新")
    force_update: Optional[bool] = Field(None, description="是否强制更新")
    force_update_reasons: Optional[List[str]] = Field(
        None, description="强制更新的具体原因列表"
    )

    minimum_version: Optional[str] = Field(None, description="最低支持版本")
    changelog: Optional[str] = Field(None, description="更新日志")
    download_url: Optional[str] = Field(None, description="下载链接")
    message: Optional[str] = Field(None, description="状态消息")
    error: Optional[str] = Field(None, description="错误信息")


class AppVersionInfo(BaseModel):
    """应用版本信息模型"""

    version_code: int = Field(..., description="版本代码")
    version_name: str = Field(..., description="版本名称")
    status: str = Field(..., description="发布状态")
    release_notes: Optional[str] = Field(None, description="发布说明")
    user_fraction: Optional[float] = Field(None, description="用户分发比例")
