from psycopg_pool import ConnectionPool

from app.core.config import global_config_loaded_from_config_yaml

from loguru import logger

# 全局连接池
_connection_pool = None
_sync_engine = None


def get_sync_engine():
    """获取全局同步数据库引擎（避免重复创建）"""
    global _sync_engine
    if _sync_engine is None:
        from sqlalchemy import create_engine

        _sync_engine = create_engine(
            global_config_loaded_from_config_yaml.database.url,
            pool_size=global_config_loaded_from_config_yaml.database.pool_size
            // 2,  # 同步引擎使用一半的连接池
            max_overflow=global_config_loaded_from_config_yaml.database.max_overflow,
            pool_timeout=global_config_loaded_from_config_yaml.database.pool_timeout,
            pool_recycle=global_config_loaded_from_config_yaml.database.pool_recycle,
            pool_pre_ping=global_config_loaded_from_config_yaml.database.pool_pre_ping,
            connect_args={
                "connect_timeout": global_config_loaded_from_config_yaml.database.connect_timeout,
                "options": "-c jit=off -c application_name=inty_sync",
            },
            echo=False,  # 禁用SQL日志
        )
        logger.info(
            f"全局同步数据库引擎已初始化 - pool_size: {global_config_loaded_from_config_yaml.database.pool_size // 2}"
        )
    return _sync_engine


def get_connection_pool():
    """获取数据库连接池"""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = ConnectionPool(
            global_config_loaded_from_config_yaml.database.url,
            min_size=global_config_loaded_from_config_yaml.database.pool_size
            // 4,  # 最小连接数
            max_size=global_config_loaded_from_config_yaml.database.pool_size,  # 最大连接数
            max_idle=300,  # 连接最大空闲时间（秒）
            max_lifetime=1800,  # 连接最大生命周期（秒）
        )
        logger.info(
            f"初始化数据库连接池: min_size={global_config_loaded_from_config_yaml.database.pool_size // 4}, max_size={global_config_loaded_from_config_yaml.database.pool_size}"
        )
    return _connection_pool