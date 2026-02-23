import os

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

API_ONLY_ENV_NAME = "INTY_API_ONLY"
_API_ONLY_TRUTHY_VALUES = {"1", "true", "yes", "on"}


def is_api_only_mode_enabled() -> bool:
    """读取环境变量并判断是否启用 API only 模式。"""
    raw_value = os.getenv(API_ONLY_ENV_NAME, "")
    normalized_value = raw_value.strip().lower()
    return normalized_value in _API_ONLY_TRUTHY_VALUES


def configure_evaluation_web_routes(
    app: FastAPI,
    static_root_dir: str,
    api_only_mode_enabled: bool,
) -> None:
    """按开关配置 evaluation 前端路由与静态资源服务。"""
    if api_only_mode_enabled:
        logger.info("API only mode enabled, skip serving evaluation web UI.")
        return

    if os.path.exists(static_root_dir):
        app.mount("/static", StaticFiles(directory=static_root_dir), name="static")

    @app.get(
        "/evaluation",
        # 此为内部运营使用 API，不对外展示
        include_in_schema=False,
    )
    async def evaluation_frontend():
        evaluation_index = os.path.join(static_root_dir, "evaluation", "index.html")
        return FileResponse(evaluation_index)

    @app.get(
        "/evaluation/{path:path}",
        # 此为内部运营使用 API，不对外展示
        include_in_schema=False,
    )
    async def evaluation_static_files(path: str):
        file_path = os.path.join(static_root_dir, "evaluation", path)
        return FileResponse(file_path)
