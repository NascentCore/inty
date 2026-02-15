# CREATED_BY_AGENT
"""
用户记忆模型

memory: 存储抽取后的记忆内容，支持多种类型（user_common=与所有 agent 的共同记忆；
         后续可扩展 user_agent=与特定角色的记忆）。对应飞书文档中的 user_memory 通用化。
memory_extraction_log: 抽取历史，用于触发判断与可观测性。
"""

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

from app.models import Base


class Memory(Base):
    """用户记忆；按 (user_id, memory_type, agent_id) 每次抽取时整批替换，仅保留最新。"""

    __tablename__ = "memory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    memory_type = Column(
        String, nullable=False, comment="user_common | user_agent | festival"
    )
    agent_id = Column(
        String, ForeignKey("agents.id"), nullable=True, comment="user_common 为 NULL"
    )
    content = Column(
        Text, nullable=False, comment="单条记忆内容，当前 Part1 整段存为一条"
    )
    extracted_at = Column(
        DateTime(timezone=True), nullable=False, comment="所属抽取批次时间"
    )
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    festival_name = Column(
        String, nullable=True, comment="节日名称，仅 memory_type=festival 时使用"
    )
    festival_date = Column(
        Date, nullable=True, comment="节日日期，仅 memory_type=festival 时使用"
    )
    delivery_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="节日记忆提示首次投递到会话的时间，仅 memory_type=festival 时使用",
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
