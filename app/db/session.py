from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import global_config_loaded_from_config_yaml
# 异步数据库引擎
async_engine = create_async_engine(
    str(global_config_loaded_from_config_yaml.database.async_url),
    pool_size=global_config_loaded_from_config_yaml.database.pool_size,  # 连接池大小，可根据需求调整
    max_overflow=global_config_loaded_from_config_yaml.database.max_overflow,  # 超出 pool_size 后最大可创建的连接数
    pool_timeout=global_config_loaded_from_config_yaml.database.pool_timeout,  # 获取连接的超时时间
    pool_recycle=global_config_loaded_from_config_yaml.database.pool_recycle,  # 连接多长时间后自动回收
    pool_pre_ping=global_config_loaded_from_config_yaml.database.pool_pre_ping,  # 检查连接可用性
    connect_args={
        "command_timeout": global_config_loaded_from_config_yaml.database.command_timeout,
        "server_settings": {
            "jit": "off",  # 关闭JIT以减少查询延迟
            "application_name": "inty_backend",
        },
    },
)
AsyncSessionLocal = sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
