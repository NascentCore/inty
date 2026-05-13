# CREATED_BY_AGENT
"""
用户记忆模型

memory: 存储抽取后的记忆内容，支持多种类型（user_common=与所有 agent 的共同记忆；
         后续可扩展 user_agent=与特定角色的记忆）。对应飞书文档中的 user_memory 通用化。
memory_extraction_log: 抽取历史，用于触发判断与可观测性。
"""

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.api.types.llm_config import LLMConfig
from app.models.base import Base


def _strip_optional_str(v: Any) -> Optional[str]:
    """Strip string and coerce empty string to None; non-str/None unchanged."""
    if v is None:
        return None
    if isinstance(v, str):
        return v.strip() or None
    return None


def _validate_llm_config_from_dict(v: Any) -> Optional[LLMConfig]:
    """None/LLMConfig pass through; dict only valid when model non-empty."""
    if v is None:
        return None
    if isinstance(v, LLMConfig):
        return v
    if isinstance(v, dict):
        if not (v.get("model") or "").strip():
            return None
        return LLMConfig.model_validate(v)
    return None


class FestivalMemoryMetadata(BaseModel):
    """
    节日记忆扩展字段（Memory.meta_data）的 Pydantic 类型。
    序列化用 model_dump(exclude_none=True)；反序列化用 model_validate(d)。
    """

    festival_name: Optional[str] = Field(None, description="节日名称")
    festival_date: Optional[str] = Field(
        None, description="节日日期（DB 存为 festival_date）"
    )
    llm_config: Optional[LLMConfig] = Field(None, description="抽取时使用的 LLM 配置")

    @field_validator("festival_name", "festival_date", mode="before")
    @classmethod
    def _strip_optional_str_fields(cls, v: Any) -> Optional[str]:
        return _strip_optional_str(v)

    @field_validator("llm_config", mode="before")
    @classmethod
    def _validate_llm_config_field(cls, v: Any) -> Optional[LLMConfig]:
        return _validate_llm_config_from_dict(v)


class DailyBondingMemoryMetadata(BaseModel):
    """
    日常记忆扩展字段（Memory.meta_data）的 Pydantic 类型。
    """

    local_date: Optional[str] = Field(None, description="本地日期（YYYY-MM-DD）")
    timezone: Optional[str] = Field(None, description="IANA 时区")
    emotional_salience: Optional[float] = Field(None, description="情绪显著性分数，0~1")
    source_message_count: Optional[int] = Field(None, description="来源消息数量")
    risk_tier: Optional[str] = Field(None, description="风险等级：low|medium|high")

    @field_validator("local_date", "timezone", "risk_tier", mode="before")
    @classmethod
    def _strip_optional_str_fields(cls, v: Any) -> Optional[str]:
        return _strip_optional_str(v)


class Memory(Base):
    """用户记忆；按 (user_id, memory_type, agent_id) 每次抽取时整批替换，仅保留最新。"""

    __tablename__ = "memory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    memory_type = Column(
        String,
        nullable=False,
        comment="user_common | user_agent | festival | daily_bonding",
    )
    agent_id = Column(
        String, ForeignKey("agents.id"), nullable=True, comment="user_common 为 NULL"
    )
    content = Column(
        Text, nullable=False, comment="单条记忆内容，当前 Part1 整段存为一条"
    )
    meta_data = Column(
        "metadata",
        JSON,
        nullable=True,
        comment=(
            "记忆扩展字段；节日记忆使用 {'festival_name': str, 'festival_date': 'YYYY-MM-DD', 'llm_config': {model, temperature, max_tokens} 可选}；"
            "日常记忆使用 {'local_date': 'YYYY-MM-DD', 'timezone': 'UTC', 'emotional_salience': 0.8, 'source_message_count': 12, 'risk_tier': 'low'}"
        ),
    )
    extracted_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="所属抽取批次时间（已废弃，仅兼容历史数据）",
    )
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    delivery_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="记忆提示首次投递到会话的时间，仅 memory_type=festival/daily_bonding 时使用",
    )
    system_notification_sent_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="节日记忆 system 推送发送时间，仅 memory_type=festival 时使用",
    )

    __table_args__ = (
        Index("ix_memory_user_type", "user_id", "memory_type"),
        Index("ix_memory_user_type_agent", "user_id", "memory_type", "agent_id"),
    )


class MemoryExtractionLog(Base):
    """记忆抽取历史，用于「上次抽取时间」及统计。"""

    __tablename__ = "memory_extraction_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    memory_type = Column(String, nullable=False)
    extracted_at = Column(DateTime(timezone=True), nullable=False)
    messages_processed_count = Column(Integer, nullable=False)
    memory_items_count = Column(Integer, nullable=False)
    status = Column(String, nullable=False, comment="success | partial | failed")
    duration_seconds = Column(Float, nullable=True, comment="当次抽取总耗时秒")
    prompt_tokens = Column(Integer, nullable=True, comment="LLM 输入 token 数")
    completion_tokens = Column(Integer, nullable=True, comment="LLM 输出 token 数")
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_memory_extraction_log_user_type", "user_id", "memory_type"),
    )


class FestivalMemoryConfig(Base):
    """节日记忆抽取配置：节日名称、日期、提示词，供定时任务与管理员执行。"""

    __tablename__ = "festival_memory_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    festival_name = Column(String, nullable=False, comment="节日名称")
    festival_date = Column(Date, nullable=False, comment="节日日期（该时区下的自然日）")
    prompt = Column(Text, nullable=False, comment="抽取提示词")
    enabled = Column(Boolean, nullable=False, default=True, comment="是否启用")
    timezone = Column(
        String,
        nullable=False,
        default="UTC",
        comment="节日日期与执行时间所属时区，IANA 名如 Asia/Shanghai",
    )
    run_at_date = Column(
        Date, nullable=True, comment="执行日期（该时区下），须 >= festival_date"
    )
    run_at_hour = Column(
        Integer, nullable=True, comment="执行时刻（该时区下本地小时），0-23"
    )
    last_run_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="最近一次被定时任务执行的时间",
    )
    min_rounds_in_window = Column(
        Integer,
        nullable=True,
        comment="窗口内最少用户消息轮数，NULL 表示默认 15",
    )
    llm_config = Column(
        JSON,
        nullable=True,
        comment="LLM 模型配置 JSON，null 表示使用全局默认",
    )
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
