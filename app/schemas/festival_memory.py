# CREATED_BY_AGENT
"""节日记忆配置与执行相关 schema"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class FestivalMemoryConfigCreate(BaseModel):
    """创建节日记忆配置"""

    festival_name: str = Field(..., description="节日名称")
    festival_date: date = Field(..., description="节日日期")
    prompt: str = Field(..., description="抽取提示词")
    enabled: bool = Field(True, description="是否启用")


class FestivalMemoryConfigUpdate(BaseModel):
    """更新节日记忆配置"""

    festival_name: Optional[str] = Field(None, description="节日名称")
    festival_date: Optional[date] = Field(None, description="节日日期")
    prompt: Optional[str] = Field(None, description="抽取提示词")
    enabled: Optional[bool] = Field(None, description="是否启用")


class FestivalMemoryConfigInDB(BaseModel):
    """节日记忆配置（数据库返回）"""

    id: int
    festival_name: str
    festival_date: date
    prompt: str
    enabled: bool

    class Config:
        from_attributes = True


class FestivalMemoryExtractionRunRequest(BaseModel):
    """立即执行节日记忆抽取请求：可指定 config_id 或直接传节日参数"""

    config_id: Optional[int] = Field(None, description="配置 ID，若指定则从表取配置")
    festival_name: Optional[str] = Field(None, description="节日名称（与 config_id 二选一）")
    festival_date: Optional[date] = Field(None, description="节日日期（与 config_id 二选一）")
    prompt: Optional[str] = Field(None, description="抽取提示词（与 config_id 二选一）")


class FestivalMemoryExtractionRunResponse(BaseModel):
    """立即执行节日记忆抽取结果"""

    total_pairs: int = Field(..., description="符合条件的 (user, agent) 对数")
    success_count: int = Field(..., description="成功写入条数")
    failed_count: int = Field(..., description="失败条数")
