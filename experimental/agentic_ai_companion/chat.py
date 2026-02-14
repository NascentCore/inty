"""入口与组装：环境加载、logger、常量，从各模块导入并组装。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import cyclopts

# 尽早加载 .env（显式路径，避免工作目录影响）
_THIS_DIR = Path(__file__).resolve().parent
_ENV_PATH = _THIS_DIR / ".env"
assert _ENV_PATH.exists(), f"环境变量文件不存在: {_ENV_PATH}"
from dotenv import load_dotenv

load_dotenv(_ENV_PATH)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_real_logger = logging.getLogger(__name__)


class _LoggerWrapper:
    """包装器：当 enabled=False 时所有 logger.* 调用不输出，用于 --debug=false 减少屏幕干扰。"""

    def __init__(self, real: logging.Logger, enabled: bool = False) -> None:
        self._real = real
        self._enabled = enabled

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def _log(self, level: str, msg: str, *args, **kwargs) -> None:
        if self._enabled:
            getattr(self._real, level)(msg, *args, **kwargs, stacklevel=3)

    def debug(self, msg: str, *args, **kwargs) -> None:
        self._log("debug", msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs) -> None:
        self._log("info", msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        self._log("warning", msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        self._log("error", msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs) -> None:
        self._log("critical", msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs) -> None:
        if self._enabled:
            self._real.exception(msg, *args, **kwargs, stacklevel=3)


logger: _LoggerWrapper = _LoggerWrapper(_real_logger, enabled=False)

import os

assert os.getenv("OPENROUTER_API_KEY") is not None, "OPENROUTER_API_KEY 未设置"

from . import clients
from . import prompts
from . import tools
from .repl import run_repl

OPENROUTER_MODEL = "google/gemini-2.5-flash"
CHAR_NAME = "Ms. Sophie Walsh"
USER_NAME = "Yaxiong Zhao"

TOOL_DEFINITIONS = tools.build_tool_definitions(_logger=logger)
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": d.name,
            "description": d.description,
            "parameters": d.parameters,
        },
    }
    for d in TOOL_DEFINITIONS
]
TOOL_EXECUTORS = {d.name: d.executor for d in TOOL_DEFINITIONS}
TOOL_TYPES = {d.name: d.type for d in TOOL_DEFINITIONS}
TOOL_CONTEXT_TYPES = {d.name: d.context_type for d in TOOL_DEFINITIONS}


def _build_system_messages(char_name: str, user_name: str):
    return prompts.build_system_messages_openai(char_name, user_name, _logger=logger)


def main(
    debug: Annotated[
        bool,
        cyclopts.Parameter(
            name="--debug", help="开启时输出 logger 日志，默认关闭以减少屏幕干扰"
        ),
    ] = False,
) -> None:
    logger.set_enabled(debug)
    if not debug:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        # 非 debug 时隐藏 Google GenAI SDK 的 INFO（如 "AFC is enabled with max remote calls"）
        logging.getLogger("google_genai").setLevel(logging.WARNING)
    logger.info("入口 main() 调用 run_repl")
    run_repl(
        char_name=CHAR_NAME,
        user_name=USER_NAME,
        model=OPENROUTER_MODEL,
        build_system_messages=_build_system_messages,
        create_openai_client=clients.create_openai_client,
        get_gemini_client=clients.get_gemini_client,
        tools=TOOLS,
        tool_executors=TOOL_EXECUTORS,
        tool_types=TOOL_TYPES,
        tool_context_types=TOOL_CONTEXT_TYPES,
        process_response_with_tools=tools.process_response_with_tools,
        logger=logger,
    )
    logger.info("run_repl 已退出")
