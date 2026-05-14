"""Ops FastAPI app: evaluation UI + full /api/v1 (evaluation-only + shared endpoints)."""

import os

from dotenv import load_dotenv
from fastapi import FastAPI
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

from app.core.build_info import build_time_utc, vcs_dirty, vcs_revision
from app.core.config import global_config_loaded_from_config_yaml
from app.api.deps import get_async_db
from app.api.utils.health_check_payload import build_health_check_data
from backend.ops.api.evaluation_web import configure_evaluation_web_routes
from app.core.agent.agent import agent_manager
from app.core.logging import init_logger
from app.external_services.firebase import init_firebase
from app.middleware.error_handler import (
    jwt_exception_handler,
    sqlalchemy_exception_handler,
    validation_error_handler,
    validation_exception_handler,
)
from app.schemas.health import HealthCheckData
from app.schemas.response import APIResponse

from backend.ops.api.v1.router import api_router

init_logger()

app = FastAPI(
    title=f"{global_config_loaded_from_config_yaml.app.name} Ops",
    description="Inty Ops – evaluation and shared API",
    version=global_config_loaded_from_config_yaml.app.version,
    openapi_url=(
        "/openapi.json" if global_config_loaded_from_config_yaml.app.debug else None
    ),
    docs_url="/docs" if global_config_loaded_from_config_yaml.app.debug else None,
    redoc_url="/redoc" if global_config_loaded_from_config_yaml.app.debug else None,
    swagger_ui_parameters=(
        {
            "persistAuthorization": True,
            "displayRequestDuration": True,
            "syntaxHighlight.theme": "obsidian",
            "tryItOutEnabled": True,
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

if global_config_loaded_from_config_yaml.app.backend_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            str(o)
            for o in global_config_loaded_from_config_yaml.app.backend_cors_origins
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(JWTError, jwt_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(ValidationError, validation_error_handler)

app.include_router(api_router)

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
static_dir = os.path.join(_ROOT, "app", "static")
configure_evaluation_web_routes(
    app=app,
    static_root_dir=static_dir,
    api_only_mode_enabled=False,
)

init_firebase()


@app.on_event("startup")
async def startup_event():
    """应用启动事件。预加载逻辑与 backend/inty 保持一致，以满足 shared 与 evaluation 对 DB/Agent 的依赖。"""
    try:
        logger.info("正在初始化 Ops 应用...")
        logger.info(
            "Build identity: release_version={} environment={} vcs_revision={} vcs_dirty={} build_time_utc={}",
            global_config_loaded_from_config_yaml.app.version,
            global_config_loaded_from_config_yaml.app.environment.value,
            vcs_revision() or "(unknown)",
            vcs_dirty(),
            build_time_utc() or "(unknown)",
        )
        await _preload_database_connections()
        async for db_session in get_async_db():
            await _preload_database_tables(db_session)
            await _preload_popular_agent_data(db_session)
            await agent_manager.initialize_popular_agents(db_session)
            break
        logger.info("Ops Agent 初始化完成")
    except Exception as e:
        logger.error(f"Ops 应用启动过程中出错: {str(e)}")


async def _preload_database_connections():
    try:
        from app.core.agent.agent import get_connection_pool, get_sync_engine
        from app.services.cache_service import cache_service

        pool = get_connection_pool()
        get_sync_engine()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        await cache_service.start_cleanup_task()
    except Exception as e:
        logger.error(f"数据库连接池初始化失败: {str(e)}")


async def _preload_database_tables(db: AsyncSession):
    try:
        from sqlalchemy import select, text

        from app.models.agent import Agent
        from app.models.chat import Chat
        from app.models.user import User

        await db.execute(select(Chat).limit(1))
        await db.execute(select(Agent).limit(1))
        await db.execute(select(User).limit(1))
        await db.execute(text("SELECT 1 FROM chat_history LIMIT 1"))
    except Exception as e:
        logger.warning(f"数据库表预初始化失败（可忽略）: {str(e)}")


async def _preload_popular_agent_data(db: AsyncSession):
    try:
        from app.services import agent_service

        popular_agents = await agent_service.get_recommended_agents(
            db, skip=0, limit=20
        )
        for agent_db in popular_agents:
            try:
                await agent_service.get_agent_for_chat(db, agent_db.id)
            except Exception as e:
                logger.warning(f"预加载Agent数据失败 {agent_db.id}: {str(e)}")
    except Exception as e:
        logger.error(f"预加载热门Agent数据失败: {str(e)}")


@app.on_event("shutdown")
async def shutdown_event():
    try:
        agent_manager.stop()
        from app.services.cache_service import cache_service

        cache_service.stop_cleanup_task()
    except Exception as e:
        logger.error(f"应用关闭过程中出错: {str(e)}")


if global_config_loaded_from_config_yaml.app.debug:

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title=app.title,
            description=app.description,
            version=app.version,
            routes=app.routes,
        )
        openapi_schema.setdefault("components", {})["securitySchemes"] = {
            "Bearer": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
        if "paths" in openapi_schema:
            for path in openapi_schema["paths"]:
                if (
                    path.endswith("/auth/login")
                    or path.endswith("/auth/register")
                    or path.endswith("/auth/guest")
                ):
                    continue
                for method in openapi_schema["paths"][path]:
                    if method.lower() in ("get", "post", "put", "delete", "patch"):
                        openapi_schema["paths"][path][method]["security"] = [
                            {"Bearer": []}
                        ]
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi


@app.get(
    "/health", response_model=APIResponse[HealthCheckData], include_in_schema=False
)
async def health():
    return APIResponse.success(data=build_health_check_data(ops=True))
