#!/usr/bin/env python3
"""
数据模型定义
定义Agent、CharacterInfo等数据结构
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class DatabaseConfig(BaseModel):
    """数据库配置模型"""

    host: str
    port: int
    user: str
    password: str
    db: str
    pool_size: Optional[int] = 10
    max_overflow: Optional[int] = 20
    pool_timeout: Optional[int] = 10
    pool_recycle: Optional[int] = 3600
    pool_pre_ping: Optional[bool] = True
    connect_timeout: Optional[int] = 5
    command_timeout: Optional[int] = 30


class AppConfig(BaseModel):
    """应用配置模型"""

    database: DatabaseConfig
    environment: Optional[str] = "development"


class CharacterInfo(BaseModel):
    """角色信息模型"""

    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    identity: Optional[str] = None
    appearance: Optional[str] = None
    apperance: Optional[str] = None  # 兼容拼写错误
    tags: Optional[str] = None


class Agent(BaseModel):
    """智能体数据模型"""

    id: str
    readable_id: Optional[str] = None
    name: str
    gender: Optional[str] = None
    personality: Optional[str] = None
    tags: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TagExtractionResult(BaseModel):
    """标签提取结果模型"""

    agent_id: str
    agent_name: str
    original_tags: Optional[List[str]] = None
    extracted_tags: List[str] = Field(default_factory=list)
    extraction_success: bool = False
    extraction_method: Optional[str] = None
    error_message: Optional[str] = None
    character_info: Optional[CharacterInfo] = None


class MigrationStats(BaseModel):
    """迁移统计信息模型"""

    total_agents: int = 0
    agents_with_personality: int = 0
    agents_with_character_info: int = 0
    agents_with_extractable_tags: int = 0
    successful_extractions: int = 0
    failed_extractions: int = 0
    updated_agents: int = 0
    skipped_agents: int = 0
    most_common_tags: Dict[str, int] = Field(default_factory=dict)
    execution_time_seconds: Optional[float] = None


class MigrationConfig(BaseModel):
    """迁移配置模型"""

    batch_size: int = 100
    dry_run: bool = True
    skip_existing_tags: bool = True
    normalize_tags: bool = True
    min_tag_length: int = 2
    max_tag_length: int = 50
    backup_before_update: bool = True
    log_level: str = "INFO"
    log_file: Optional[str] = None
