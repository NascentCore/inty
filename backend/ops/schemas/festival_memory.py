# CREATED_BY_AGENT
"""节日记忆配置与执行相关 schema"""

from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator, model_validator

from app.api.types.llm_config import LLMConfig

RUN_AT_HOUR_MIN = 0
RUN_AT_HOUR_MAX = 23


def _validate_iana_timezone(v: str) -> str:
    try:
        ZoneInfo(v)
    except ZoneInfoNotFoundError:
        raise ValueError(f"Invalid IANA timezone: {v}")
    return v


class FestivalMemoryConfigCreate(BaseModel):
    """创建节日记忆配置"""

    festival_name: str = Field(..., description="节日名称")
    festival_date: date = Field(..., description="节日日期（该时区下的自然日）")
    prompt: str = Field(..., description="抽取提示词")
    enabled: bool = Field(True, description="是否启用")
    timezone: str = Field(
        default="UTC",
        description="节日日期与执行时间所属时区，IANA 名如 Asia/Shanghai",
    )
    run_at_date: date = Field(
        ..., description="执行日期（该时区下），须不早于节日日期"
    )
    run_at_hour: int = Field(
        ...,
        ge=RUN_AT_HOUR_MIN,
        le=RUN_AT_HOUR_MAX,
        description="执行时刻（该时区下本地小时）0-23",
    )
    min_rounds_in_window: Optional[int] = Field(
        None,
        ge=1,
        description="窗口内最少用户消息轮数，不传则默认 15",
    )
    llm_config: Optional[LLMConfig] = Field(
        None,
        description="LLM 模型配置 JSON，null 表示使用全局默认",
    )

    @model_validator(mode="after")
    def validate_timezone(self) -> "FestivalMemoryConfigCreate":
        _validate_iana_timezone(self.timezone)
        return self

    @model_validator(mode="after")
    def run_at_not_before_festival(self) -> "FestivalMemoryConfigCreate":
        if self.run_at_date < self.festival_date:
            raise ValueError(
                "Run date cannot be earlier than the festival date"
            )
        return self


class FestivalMemoryConfigUpdate(BaseModel):
    """更新节日记忆配置"""

    festival_name: Optional[str] = Field(None, description="节日名称")
    festival_date: Optional[date] = Field(
        None, description="节日日期（该时区下的自然日）"
    )
    prompt: Optional[str] = Field(None, description="抽取提示词")
    enabled: Optional[bool] = Field(None, description="是否启用")
    timezone: Optional[str] = Field(
        None,
        description="节日日期与执行时间所属时区，IANA 名如 Asia/Shanghai",
    )
    run_at_date: Optional[date] = Field(
        None, description="执行日期（该时区下），须不早于节日日期"
    )
    run_at_hour: Optional[int] = Field(
        None,
        ge=RUN_AT_HOUR_MIN,
        le=RUN_AT_HOUR_MAX,
        description="执行时刻（该时区下本地小时）0-23",
    )
    min_rounds_in_window: Optional[int] = Field(
        None,
        ge=1,
        description="窗口内最少用户消息轮数，不传则默认 15",
    )
    llm_config: Optional[LLMConfig] = Field(
        None,
        description="LLM 模型配置 JSON，不传表示不更新，传 null 表示改为默认模型",
    )

    @model_validator(mode="after")
    def validate_timezone_and_run_at(self) -> "FestivalMemoryConfigUpdate":
        if self.timezone is not None:
            _validate_iana_timezone(self.timezone)
        run_at = self.run_at_date
        festival = self.festival_date
        if run_at is not None and festival is not None and run_at < festival:
            raise ValueError(
                "Run date cannot be earlier than the festival date"
            )
        return self


class FestivalMemoryConfigInDB(BaseModel):
    """节日记忆配置（数据库返回）"""

    id: int
    festival_name: str
    festival_date: date
    prompt: str
    enabled: bool
    timezone: str = Field(..., description="节日与执行时间所属时区，IANA 名")
    run_at_date: Optional[date] = Field(
        None, description="执行日期（该时区下）"
    )
    run_at_hour: Optional[int] = Field(
        None, description="执行时刻（该时区下本地小时）0-23"
    )
    last_run_at: Optional[datetime] = Field(
        None, description="最近一次被定时任务执行的时间"
    )
    min_rounds_in_window: Optional[int] = Field(
        None, description="窗口内最少用户消息轮数，NULL 表示默认 15"
    )
    llm_config: Optional[LLMConfig] = Field(
        None, description="LLM 模型配置 JSON，null 表示使用全局默认"
    )

    @field_validator("llm_config", mode="before")
    @classmethod
    def _llm_config_from_dict(cls, v: object) -> Optional[LLMConfig]:
        if v is None:
            return None
        if isinstance(v, LLMConfig):
            return v
        if isinstance(v, dict):
            return LLMConfig.model_validate(v)
        raise ValueError(
            f"llm_config must be None, dict, or LLMConfig, got {type(v).__name__}"
        )

    class Config:
        from_attributes = True


class FestivalMemoryExtractionRunRequest(BaseModel):
    """立即执行节日记忆抽取请求：可指定 config_id 或直接传节日参数"""

    config_id: Optional[int] = Field(
        None, description="配置 ID，若指定则从表取配置"
    )
    festival_name: Optional[str] = Field(
        None, description="节日名称（与 config_id 二选一）"
    )
    festival_date: Optional[date] = Field(
        None, description="节日日期（与 config_id 二选一）"
    )
    prompt: Optional[str] = Field(
        None, description="抽取提示词（与 config_id 二选一）"
    )
    timezone: Optional[str] = Field(
        default="UTC",
        description="节日日期所属时区（仅当未传 config_id 时用于窗口计算）",
    )
    min_rounds_in_window: Optional[int] = Field(
        None,
        ge=1,
        description="窗口内最少用户消息轮数（仅当未传 config_id 时生效），不传则默认 15",
    )

    @model_validator(mode="after")
    def validate_timezone(self) -> "FestivalMemoryExtractionRunRequest":
        if self.timezone:
            _validate_iana_timezone(self.timezone)
        return self


class FestivalMemoryExtractionRunResponse(BaseModel):
    """立即执行节日记忆抽取结果"""

    total_pairs: int = Field(..., description="符合条件的 (user, agent) 对数")
    success_count: int = Field(..., description="成功写入条数")
    failed_count: int = Field(..., description="失败条数")
