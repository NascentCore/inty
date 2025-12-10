# CREATED_BY_AGENT
"""
配置管理 - 复用主应用的配置逻辑
IntyEval 使用与主应用相同的配置系统
"""

# 直接导入主应用的配置，确保配置一致性
from app.core.config import (
    global_config_loaded_from_config_yaml,
)

__all__ = ["global_config_loaded_from_config_yaml"]

