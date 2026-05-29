from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from jose.exceptions import JWTError
from loguru import logger
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

# 系统级别行为配置通过环境变量配置，比如日志级别、LangSmith追踪等。
load_dotenv()

# ！！！ 这个 import 必须在所有导入其他应用代码之前。
# 因为这里设置了 LangSmith 环境变量
# 如果不在最前面，有可能导致环境变量未注入导致 LangSmith tracing 获得空的环境变量，从而失效
from app.core.build_info import build_time_utc, vcs_dirty, vcs_revision
from app.core.config import global_config_loaded_from_config_yaml

from app.api.deps import get_async_db
from app.api.utils.health_check_payload import build_health_check_data
from app.api.v1.router import api_router
from app.core.agent.agent import agent_manager
from app.core.logging import init_logger
from app.external_services.firebase import init_firebase
from app.middleware.error_handler import (
    http_exception_handler,
    jwt_exception_handler,
    sqlalchemy_exception_handler,
    unhandled_exception_handler,
    validation_error_handler,
    validation_exception_handler,
)
from app.middleware.observability import (
    ObservabilityMiddleware,
    metrics_response,
)
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.schemas.health import HealthCheckData
from app.schemas.response import APIResponse
from app.utils.config import Environment

init_logger()

# 根据debug模式决定是否开启OpenAPI docs
app = FastAPI(
    title=global_config_loaded_from_config_yaml.app.name,
    description="InTy",
    version=global_config_loaded_from_config_yaml.app.version,
    # 只在debug模式下开启OpenAPI docs
    openapi_url=(
        "/openapi.json"
        if global_config_loaded_from_config_yaml.app.debug
        else None
    ),
    docs_url=(
        "/docs" if global_config_loaded_from_config_yaml.app.debug else None
    ),
    redoc_url=(
        "/redoc" if global_config_loaded_from_config_yaml.app.debug else None
    ),
    # Swagger UI参数配置（仅在debug模式下生效）
    swagger_ui_parameters=(
        {
            "persistAuthorization": True,
            "displayRequestDuration": True,
            "syntaxHighlight.theme": "obsidian",
            "tryItOutEnabled": True,
            "requestSnippetsEnabled": True,
            "defaultModelsExpandDepth": 3,
            "defaultModelExpandDepth": 3,
        }
        if global_config_loaded_from_config_yaml.app.debug
        else {}
    ),
    contact={
        "name": "InTy",
        "url": "http://inty.cc/",
        "email": "dev@inty.cc",
    },
)

# Set all CORS enabled origins
if global_config_loaded_from_config_yaml.app.backend_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            str(origin)
            for origin in global_config_loaded_from_config_yaml.app.backend_cors_origins
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_middleware(ObservabilityMiddleware)

# Register error handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(JWTError, jwt_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(ValidationError, validation_error_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(api_router)


# 初始化 Firebase
init_firebase()


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    try:
        logger.info("正在初始化应用...")
        logger.info(
            "Build identity: release_version={} environment={} vcs_revision={} vcs_dirty={} build_time_utc={}",
            global_config_loaded_from_config_yaml.app.version,
            global_config_loaded_from_config_yaml.app.environment.value,
            vcs_revision() or "(unknown)",
            vcs_dirty(),
            build_time_utc() or "(unknown)",
        )
        logger.debug(
            f"数据库 URL: {global_config_loaded_from_config_yaml.database.url}"
        )
        logger.debug(
            f"异步数据库 URL: {global_config_loaded_from_config_yaml.database.async_url}"
        )

        # 0. 预初始化数据库连接池和chat_history表
        await _preload_database_connections()

        # 获取数据库会话
        async for db_session in get_async_db():
            # 1. 预初始化数据库表结构（提升性能）
            await _preload_database_tables(db_session)

            # 2. 预加载热门Agent数据到缓存
            await _preload_popular_agent_data(db_session)

            # 3. 初始化常用Agent实例
            await agent_manager.initialize_popular_agents(db_session)
            break  # 只需要一次初始化
        logger.info("Agent初始化完成")

    except Exception as e:
        logger.error(f"应用启动过程中出错: {str(e)}")


async def _preload_database_connections():
    """预初始化数据库连接池和chat_history表"""
    try:
        logger.info("开始预初始化数据库连接池...")

        # 1. 预初始化Agent系统的连接池
        from app.core.agent.agent import get_connection_pool, get_sync_engine

        # 预初始化连接池（这会创建min_size数量的连接）
        pool = get_connection_pool()
        logger.info(f"连接池预初始化完成: {pool.name}")

        # 预初始化同步引擎
        sync_engine = get_sync_engine()
        logger.info("同步数据库引擎预初始化完成")

        # 3. 预热连接池 - 执行一些轻量级查询来预热连接
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        logger.info("连接池预热完成")

        # 4. 启动缓存清理任务
        from app.services.cache_service import cache_service

        await cache_service.start_cleanup_task()
        logger.info("缓存服务启动完成")

        # 5. 启动离线 maintenance heartbeat（无 presence 时持续演化 companion 记忆）
        from app.services.agentic_companion.offline_maintenance_scheduler import (
            start_offline_maintenance_scheduler,
        )

        await start_offline_maintenance_scheduler()

        logger.info("数据库连接池初始化完成")

    except Exception as e:
        logger.error(f"数据库连接池初始化失败: {str(e)}")
        # 不抛出异常，让应用继续启动


async def _preload_popular_agent_data(db: AsyncSession):
    """预加载热门Agent数据到缓存"""
    try:
        logger.info("开始预加载热门Agent数据到缓存...")

        from app.services import agent_service

        # 获取推荐的Agent作为热门Agent进行预加载
        popular_agents = await agent_service.get_recommended_agents(
            db, skip=0, limit=20
        )

        # 为每个热门Agent预加载聊天数据到缓存
        preloaded_count = 0
        for agent_db in popular_agents:
            try:
                # 使用轻量级方法预加载数据（这会自动缓存）
                agent_data = await agent_service.get_agent_for_chat(
                    db, agent_db.id
                )
                if agent_data:
                    preloaded_count += 1
                    logger.debug(f"预加载Agent数据: {agent_data['name']}")
            except Exception as e:
                logger.warning(f"预加载Agent数据失败 {agent_db.id}: {str(e)}")

        logger.info(
            f"热门Agent数据预加载完成: {preloaded_count}/{len(popular_agents)}"
        )

    except Exception as e:
        logger.error(f"预加载热门Agent数据失败: {str(e)}")
        # 不抛出异常，让应用继续启动


async def _preload_database_tables(db: AsyncSession):
    """预加载数据库表结构以提升查询性能"""
    try:
        logger.info("开始预初始化数据库表结构...")

        # 预热聊天表查询，确保表结构已加载
        from sqlalchemy import select

        # 执行一个简单的查询来预热表结构
        await db.execute(select(Chat).limit(1))
        await db.execute(select(Agent).limit(1))
        await db.execute(select(User).limit(1))

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
        from app.core.companion_harness.companion.websocket_coordinator import (
            ChatWsInflightShutdownRegistry,
        )

        logger.info("正在取消进行中的 chat WebSocket companion turn...")
        await ChatWsInflightShutdownRegistry.cancel_all_registered()

        logger.info("正在停止Agent管理器...")
        agent_manager.stop()
        logger.info("Agent管理器已停止")

        # 停止缓存服务
        from app.services.cache_service import cache_service

        cache_service.stop_cleanup_task()
        logger.info("缓存服务已停止")

        # 停止离线 maintenance heartbeat
        from app.services.agentic_companion.offline_maintenance_scheduler import (
            stop_offline_maintenance_scheduler,
        )

        await stop_offline_maintenance_scheduler()

    except Exception as e:
        logger.error(f"应用关闭过程中出错: {str(e)}")


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=global_config_loaded_from_config_yaml.app.name,
        description=app.description,
        version=global_config_loaded_from_config_yaml.app.version,
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
            """,
        }
    }

    # 为所有路由添加安全要求，除了登录和注册接口
    if "paths" in openapi_schema:
        for path in openapi_schema["paths"]:
            # 跳过认证相关的路由
            if (
                path.endswith("/auth/login")
                or path.endswith("/auth/register")
                or path.endswith("/auth/guest")
            ):
                continue

            # 为路径下的所有操作添加安全要求
            for method in openapi_schema["paths"][path]:
                if method.lower() in ("get", "post", "put", "delete", "patch"):
                    openapi_schema["paths"][path][method]["security"] = [
                        {"Bearer": []}
                    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


# 只在debug模式下设置自定义OpenAPI
if global_config_loaded_from_config_yaml.app.debug:
    app.openapi = custom_openapi


@app.get(
    "/", response_model=APIResponse[HealthCheckData], include_in_schema=False
)
async def root():
    """健康检查接口"""
    return APIResponse.success(data=build_health_check_data(ops=False))


@app.get("/metrics", include_in_schema=False)
async def metrics():
    if (
        not global_config_loaded_from_config_yaml.app.debug
        and global_config_loaded_from_config_yaml.app.environment
        != Environment.TEST
    ):
        raise HTTPException(status_code=404, detail="Not Found")
    return metrics_response()
