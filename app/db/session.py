from typing import Generator, AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.core.config import settings

# # 同步数据库引擎
# engine = create_engine(
#     str(settings.database.url),
#     pool_pre_ping=True,
# )
# SessionLocal = sessionmaker(
#     autocommit=False, 
#     autoflush=False, 
#     bind=engine
# )

# def get_db() -> Generator:
#     """获取数据库会话"""
#     try:
#         db = SessionLocal()
#         yield db
#     finally:
#         db.close() 

# 异步数据库引擎
async_engine = create_async_engine(
    str(settings.database.async_url),
    pool_size=settings.database.pool_size,         # 连接池大小，可根据需求调整
    max_overflow=settings.database.max_overflow,   # 超出 pool_size 后最大可创建的连接数
    pool_timeout=settings.database.pool_timeout,   # 获取连接的超时时间
    pool_recycle=settings.database.pool_recycle,   # 连接多长时间后自动回收
    pool_pre_ping=settings.database.pool_pre_ping, # 检查连接可用性
    connect_args={
        "command_timeout": settings.database.command_timeout,
        "server_settings": {
            "jit": "off",  # 关闭JIT以减少查询延迟
            "application_name": "inty_backend",
        },
    }
)
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
