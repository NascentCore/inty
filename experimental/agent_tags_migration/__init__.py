#!/usr/bin/env python3
"""
Agent Tags Migration Package

从智能体的personality字段中提取标签信息并迁移到tags字段的工具包。

主要组件:
- TagParser: 标签解析器
- DatabaseManager: 数据库操作管理器
- TagMigrator: 主要迁移逻辑
- 各种数据模型和配置类

使用方法:
    python extract_tags_from_personality.py --analyze
    python extract_tags_from_personality.py --update
"""

__version__ = "1.0.0"
__author__ = "Claude Code"
__description__ = "Agent Tags Migration Tool"

from .models import (
    Agent,
    CharacterInfo,
    TagExtractionResult,
    MigrationStats,
    MigrationConfig,
    DatabaseConfig,
    AppConfig,
)

from .tag_parser import TagParser
from .database import DatabaseManager, create_database_manager, load_config_from_yaml
from .logger import setup_logger, MigrationLogger

__all__ = [
    "Agent",
    "CharacterInfo",
    "TagExtractionResult",
    "MigrationStats",
    "MigrationConfig",
    "DatabaseConfig",
    "AppConfig",
    "TagParser",
    "DatabaseManager",
    "create_database_manager",
    "load_config_from_yaml",
    "setup_logger",
    "MigrationLogger",
]
