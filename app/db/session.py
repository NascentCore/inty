from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import global_config_loaded_from_config_yaml
from app.models.registry import load_model_modules

load_model_modules()

_db = global_config_loaded_from_config_yaml.database

# 异步数据库引擎（主库）
async_engine = create_async_engine(
    str(_db.async_url),
    pool_size=_db.pool_size,
    max_overflow=_db.max_overflow,
    pool_timeout=_db.pool_timeout,
    pool_recycle=_db.pool_recycle,
    pool_pre_ping=_db.pool_pre_ping,
    connect_args={
        "command_timeout": _db.command_timeout,
        "server_settings": {
            "jit": "off",
            "application_name": "inty_backend",
        },
    },
)
AsyncSessionLocal = sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)

# 只读副本引擎（用于日报周报等读多写少场景，未配置时为空）
_replica_url = _db.async_replica_url
async_replica_engine = (
    create_async_engine(
        str(_replica_url),
        pool_size=_db.pool_size,
        max_overflow=_db.max_overflow,
        pool_timeout=_db.pool_timeout,
        pool_recycle=_db.pool_recycle,
        pool_pre_ping=_db.pool_pre_ping,
        connect_args={
            "command_timeout": _db.command_timeout,
            "server_settings": {
                "jit": "off",
                "application_name": "inty_backend_replica",
            },
        },
    )
    if _replica_url
    else None
)
AsyncSessionLocalReplica: Optional[type] = (
    sessionmaker(
        bind=async_replica_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    if async_replica_engine is not None
    else None
)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_async_replica_db() -> AsyncGenerator[AsyncSession, None]:
    if AsyncSessionLocalReplica is not None:
        async with AsyncSessionLocalReplica() as session:
            yield session
    else:
        async with AsyncSessionLocal() as session:
            yield session
