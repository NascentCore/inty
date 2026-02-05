# CREATED_BY_AGENT
"""节日记忆配置与执行相关 schema"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


RUN_AT_HOUR_MIN = 0
RUN_AT_HOUR_MAX = 23


class FestivalMemoryConfigCreate(BaseModel):
    """创建节日记忆配置"""

    festival_name: str = Field(..., description="节日名称")
    festival_date: date = Field(..., description="节日日期")
    prompt: str = Field(..., description="抽取提示词")
    enabled: bool = Field(True, description="是否启用")
    run_at_date: date = Field(..., description="执行日期，须不早于节日日期")
    run_at_hour: int = Field(..., ge=RUN_AT_HOUR_MIN, le=RUN_AT_HOUR_MAX, description="执行时刻 UTC 小时 0-23")

    @model_validator(mode="after")
    def run_at_not_before_festival(self) -> "FestivalMemoryConfigCreate":
        if self.run_at_date < self.festival_date:
            raise ValueError("执行日期不能早于节日日期")
        return self


class FestivalMemoryConfigUpdate(BaseModel):
    """更新节日记忆配置"""

    festival_name: Optional[str] = Field(None, description="节日名称")
    festival_date: Optional[date] = Field(None, description="节日日期")
    prompt: Optional[str] = Field(None, description="抽取提示词")
    enabled: Optional[bool] = Field(None, description="是否启用")
    run_at_date: Optional[date] = Field(None, description="执行日期，须不早于节日日期")
    run_at_hour: Optional[int] = Field(None, ge=RUN_AT_HOUR_MIN, le=RUN_AT_HOUR_MAX, description="执行时刻 UTC 小时 0-23")

    @model_validator(mode="after")
    def run_at_not_before_festival(self) -> "FestivalMemoryConfigUpdate":
        run_at = self.run_at_date
        festival = self.festival_date
        if run_at is not None and festival is not None and run_at < festival:
            raise ValueError("执行日期不能早于节日日期")
        return self


class FestivalMemoryConfigInDB(BaseModel):
    """节日记忆配置（数据库返回）"""

    id: int
    festival_name: str
    festival_date: date
    prompt: str
    enabled: bool
    run_at_date: Optional[date] = Field(None, description="执行日期")
    run_at_hour: Optional[int] = Field(None, description="执行时刻 UTC 小时")
    last_run_at: Optional[datetime] = Field(None, description="最近一次被定时任务执行的时间")

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
