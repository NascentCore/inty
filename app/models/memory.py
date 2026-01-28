# CREATED_BY_AGENT
"""
用户记忆模型

memory: 存储抽取后的记忆内容，支持多种类型（user_common=与所有 agent 的共同记忆；
         后续可扩展 user_agent=与特定角色的记忆）。对应飞书文档中的 user_memory 通用化。
memory_extraction_log: 抽取历史，用于触发判断与可观测性。
"""

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.sql import func

from app.models import Base


class Memory(Base):
    """用户记忆；按 (user_id, memory_type, agent_id) 每次抽取时整批替换，仅保留最新。"""

    __tablename__ = "memory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    memory_type = Column(String, nullable=False, comment="user_common | user_agent")
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
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_memory_extraction_log_user_type", "user_id", "memory_type"),
    )
