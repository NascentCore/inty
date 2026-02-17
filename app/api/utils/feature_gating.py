"""
所有用于判断功能是否启用的 API 都放在这里。
"""

from app.core.config import global_config_loaded_from_config_yaml

def is_festival_memory_enabled(app_version_code: int | None) -> bool:
    """
    当且仅当客户端提供了 app version code 且大于等于配置的最小版本时才启用节日记忆功能。
    未传版本或版本低于配置值时返回 False，防止过老客户端无法处理节日记忆数据。
    """
    return app_version_code is not None and app_version_code >= global_config_loaded_from_config_yaml.app.min_app_version_code_for_festival_memory
