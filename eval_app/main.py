# CREATED_BY_AGENT
"""
IntyEval - 内部运营工具 FastAPI 应用
用于评测系统和用户数据分析
"""

import os
import sentry_sdk
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from jose.exceptions import JWTError
from loguru import logger
from pydantic import BaseModel, ValidationError
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sqlalchemy.exc import SQLAlchemyError

# ！！！ 这个 import 必须在所有导入其他应用代码之前。
# 因为这里设置了 LangSmith 环境变量
from app.core.config import global_config_loaded_from_config_yaml
from app.core.logging import init_logger
from app.external_services.firebase import init_firebase
from app.middleware.error_handler import (
    jwt_exception_handler,
    sqlalchemy_exception_handler,
    validation_error_handler,
    validation_exception_handler,
)
from app.schemas.response import APIResponse
from eval_app.api.v1.router import api_router

init_logger()


def init_sentry():
    """初始化 Sentry 错误监控"""
    try:
        sentry_config = global_config_loaded_from_config_yaml.sentry

        if not sentry_config.enabled:
            logger.info("Sentry 监控未启用")
            return

        if not sentry_config.dsn:
            logger.warning("Sentry DSN 未配置，跳过初始化")
            return

        logger.info("正在初始化 Sentry 错误监控...")

        sentry_sdk.init(
            dsn=sentry_config.dsn,
            environment=global_config_loaded_from_config_yaml.app.environment.value,
            send_default_pii=False,
            integrations=[
                FastApiIntegration(),
                StarletteIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
            ],
            server_name=f"{global_config_loaded_from_config_yaml.app.name}-eval",
            release=global_config_loaded_from_config_yaml.app.version,
            auto_enabling_integrations=False,
            traces_sample_rate=sentry_config.traces_sample_rate,
        )

        logger.info(
            f"Sentry 错误监控初始化完成 (项目: {global_config_loaded_from_config_yaml.app.name}-eval, 环境: {global_config_loaded_from_config_yaml.app.environment.value})"
        )

    except Exception as e:
        logger.error(f"初始化 Sentry 错误监控失败: {str(e)}")


init_sentry()

# 创建 FastAPI 应用
app = FastAPI(
    title=f"{global_config_loaded_from_config_yaml.app.name} Evaluation",
    description="IntyEval - 内部运营工具，用于评测系统和用户数据分析",
    version=global_config_loaded_from_config_yaml.app.version,
    # 只在debug模式下开启OpenAPI docs
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
            "requestSnippetsEnabled": True,
            "defaultModelsExpandDepth": 3,
            "defaultModelExpandDepth": 3,
        }
        if global_config_loaded_from_config_yaml.app.debug
        else {}
    ),
    contact={
        "name": "InTy Evaluation",
        "url": "http://inty.cc/",
        "email": "dev@inty.cc",
    },
)

# 设置 CORS - IntyEval 是内部工具，可能需要更宽松的 CORS 配置
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

# 注册错误处理器
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(JWTError, jwt_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(ValidationError, validation_error_handler)

# 注册 API 路由
app.include_router(api_router)

# 配置静态文件服务 - 用于评测系统前端
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 添加前端应用路由
@app.get(
    "/evaluation",
    # 此为内部运营使用 API，不对外展示
    include_in_schema=False,
)
async def evaluation_frontend():
    evaluation_index = os.path.join(static_dir, "evaluation", "index.html")
    if os.path.exists(evaluation_index):
        return FileResponse(evaluation_index)
    else:
        logger.warning(f"Evaluation 前端文件不存在: {evaluation_index}")
        return {"message": "Evaluation frontend not found"}


@app.get(
    "/evaluation/{path:path}",
    # 此为内部运营使用 API，不对外展示
    include_in_schema=False,
)
async def evaluation_static_files(path: str):
    file_path = os.path.join(static_dir, "evaluation", path)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        logger.warning(f"Evaluation 静态文件不存在: {file_path}")
        return {"message": "File not found"}


# 初始化 Firebase
init_firebase()


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    try:
        logger.info("正在初始化 IntyEval 应用...")
        logger.debug(
            f"数据库 URL: {global_config_loaded_from_config_yaml.database.url}"
        )
        logger.debug(
            f"异步数据库 URL: {global_config_loaded_from_config_yaml.database.async_url}"
        )

        # IntyEval 不需要预加载 agent 数据等，只需要确保数据库连接正常
        from app.api.deps import get_async_db

        async for db_session in get_async_db():
            # 简单的数据库连接测试
            from sqlalchemy import text

            await db_session.execute(text("SELECT 1"))
            break

        logger.info("IntyEval 应用初始化完成")

    except Exception as e:
        logger.error(f"IntyEval 应用启动过程中出错: {str(e)}")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    try:
        logger.info("正在关闭 IntyEval 应用...")
        # IntyEval 不需要特殊的关闭逻辑
        logger.info("IntyEval 应用已关闭")

    except Exception as e:
        logger.error(f"IntyEval 应用关闭过程中出错: {str(e)}")


class HealthCheckData(BaseModel):
    """健康检查数据结构"""

    app_name: str
    version: str


@app.get("/", response_model=APIResponse[HealthCheckData], include_in_schema=False)
async def root():
    """健康检查接口"""
    return APIResponse.success(
        data=HealthCheckData(
            app_name=f"{global_config_loaded_from_config_yaml.app.name} Evaluation",
            version=global_config_loaded_from_config_yaml.app.version,
        )
    )

