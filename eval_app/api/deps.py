# CREATED_BY_AGENT
"""
依赖注入 - 复用主应用的依赖函数
IntyEval 使用与主应用相同的认证和数据库会话逻辑
"""

# 直接导入主应用的依赖函数
from app.api.deps import (
    get_async_db,
    get_current_active_user,
    get_current_user,
    get_db,
    oauth2_scheme,
)

__all__ = [
    "get_async_db",
    "get_current_active_user",
    "get_current_user",
    "get_db",
    "oauth2_scheme",
]

