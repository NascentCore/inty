from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from jose.exceptions import JWTError
from pydantic import ValidationError

from app.core.config import settings
from app.api.v1.api import api_router
from app.middleware.error_handler import (
    validation_exception_handler,
    jwt_exception_handler,
    sqlalchemy_exception_handler,
    validation_error_handler
)
from app.core.logging import init_logger
from app.core.agent.agent import agent_manager
from app.api.deps import get_async_db
from app.services.keep_talking_service import keep_talking_service
from loguru import logger
from app.core.firebase import init_firebase

init_logger()

app = FastAPI(
    title=settings.app.name,
    description="""
    InTy 后端服务
    """,
    version="1.0.0",
    openapi_url=f"{settings.app.api_v1_prefix}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "syntaxHighlight.theme": "obsidian",
        "tryItOutEnabled": True,
        "requestSnippetsEnabled": True,
        "defaultModelsExpandDepth": 3,
        "defaultModelExpandDepth": 3,
    }
)

# Set all CORS enabled origins
if settings.app.backend_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.app.backend_cors_origins],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Register error handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(JWTError, jwt_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(ValidationError, validation_error_handler)

app.include_router(api_router, prefix=settings.app.api_v1_prefix)

# 初始化 Firebase
init_firebase()

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    try:
        logger.info("正在初始化应用...")
        # 获取数据库会话
        async for db_session in get_async_db():
            # 1. 预初始化数据库表结构（提升性能）
            await _preload_database_tables(db_session)
            
            # 2. 初始化常用Agent
            await agent_manager.initialize_popular_agents(db_session)
            break  # 只需要一次初始化
        logger.info("Agent初始化完成")
        
        # 根据配置决定是否启动Keep Talking服务
        if settings.keep_talking.enabled:
            logger.info("正在启动Keep Talking服务...")
            await keep_talking_service.start()
            logger.info("Keep Talking服务已启动")
        else:
            logger.info("Keep Talking服务已禁用，跳过启动")
    except Exception as e:
        logger.error(f"应用启动过程中出错: {str(e)}")

async def _preload_database_tables(db: AsyncSession):
    """预加载数据库表结构以提升查询性能"""
    try:
        logger.info("开始预初始化数据库表结构...")
        
        # 预热聊天表查询，确保表结构已加载
        from app import models
        from sqlalchemy import select
        
        # 执行一个简单的查询来预热表结构
        await db.execute(select(models.Chat).limit(1))
        await db.execute(select(models.Agent).limit(1))
        await db.execute(select(models.User).limit(1))
        
        # 预热chat_history表（PostgreSQL）
        from sqlalchemy import text
        await db.execute(text("SELECT 1 FROM chat_history LIMIT 1"))
        
        logger.info("数据库表结构预初始化完成")
    except Exception as e:
        logger.warning(f"数据库表预初始化失败（可忽略）: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    try:
        # 只有在服务启用时才需要停止
        if settings.keep_talking.enabled:
            logger.info("正在停止Keep Talking服务...")
            await keep_talking_service.stop()
            logger.info("Keep Talking服务已停止")
        else:
            logger.info("Keep Talking服务未启用，无需停止")
        
        logger.info("正在停止Agent管理器...")
        agent_manager.stop()
        logger.info("Agent管理器已停止")
    except Exception as e:
        logger.error(f"应用关闭过程中出错: {str(e)}")

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=settings.app.name,
        version="1.0.0",
        description=app.description,
        routes=app.routes,
    )
    
    # 添加安全定义
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": """
            输入格式为: your_token
            注意: 不需要Bearer前缀
            """
        }
    }
    
    # 为所有路由添加安全要求，除了登录和注册接口
    if "paths" in openapi_schema:
        for path in openapi_schema["paths"]:
            # 跳过认证相关的路由
            if path.endswith("/auth/login") or path.endswith("/auth/register") or path.endswith("/auth/guest"):
                continue
                
            # 为路径下的所有操作添加安全要求
            for method in openapi_schema["paths"][path]:
                if method.lower() in ("get", "post", "put", "delete", "patch"):
                    openapi_schema["paths"][path][method]["security"] = [{"Bearer": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.get("/")
async def root():
    """健康检查接口"""
    return {
        "code": 200,
        "message": "success",
        "data": {
            "app_name": settings.app.name,
            "version": "1.0.0"
        }
    } 