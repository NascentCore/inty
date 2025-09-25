from typing import List, Optional
from pydantic import BaseModel, Field


class VersionCheckRequest(BaseModel):
    """版本检查请求模型"""

    version: str = Field(..., description="客户端版本代码", example="123")
    platform: str = Field(default="android", description="平台类型", example="android")


class VersionCheckResponse(BaseModel):
    """版本检查响应模型"""

    current_version: str = Field(..., description="当前客户端版本")
    latest_version: str = Field(..., description="最新可用版本")
    latest_version_code: Optional[int] = Field(None, description="最新版本代码")
    update_required: bool = Field(..., description="是否需要更新")
    force_update: bool = Field(..., description="是否强制更新")
    force_update_reasons: Optional[List[str]] = Field(
        None, description="强制更新的具体原因列表"
    )
    minimum_version: str = Field(..., description="最低支持版本")
    changelog: Optional[str] = Field(None, description="更新日志")
    download_url: str = Field(..., description="下载链接")
    message: str = Field(..., description="状态消息")
    error: Optional[str] = Field(None, description="错误信息")


class AppVersionInfo(BaseModel):
    """应用版本信息模型"""

    version_code: int = Field(..., description="版本代码")
    version_name: str = Field(..., description="版本名称")
    status: str = Field(..., description="发布状态")
    release_notes: Optional[str] = Field(None, description="发布说明")
    user_fraction: Optional[float] = Field(None, description="用户分发比例")
