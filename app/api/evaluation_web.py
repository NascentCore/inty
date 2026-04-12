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

    evaluation_static_dir = os.path.join(static_root_dir, "evaluation")
    evaluation_index = os.path.join(evaluation_static_dir, "index.html")

    @app.get(
        "/",
        # 迁移步骤：将评测页入口切到根路径，同时保留 /evaluation 兼容旧链接和旧构建资源前缀。
        include_in_schema=False,
    )
    async def evaluation_frontend_root():
        return FileResponse(evaluation_index)

    @app.get(
        "/evaluation",
        # 此为内部运营使用 API，不对外展示
        include_in_schema=False,
    )
    async def evaluation_frontend_legacy():
        return FileResponse(evaluation_index)

    @app.get(
        "/evaluation/{path:path}",
        # 此为内部运营使用 API，不对外展示
        include_in_schema=False,
    )
    async def evaluation_static_files(path: str):
        # GET /evaluation/ matches this route with an empty path; join(..., "") is the directory, not a file.
        segment = (path or "").strip("/")
        if not segment:
            return FileResponse(evaluation_index)
        file_path = os.path.join(evaluation_static_dir, segment)
        return FileResponse(file_path)
