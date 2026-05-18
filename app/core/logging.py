"""
init_logger() should be called at the very beginning of the application.
Afterwards, one should just use loguru.logger in the code:

```python
from loguru import logger

def your_function():
    logger.info("Hello, world!")
```

The Inty, Ops, and push worker entry modules call ``load_dotenv()`` (``python-dotenv``)
before importing ``app``, loading ``.env`` from the process current working directory
(assume repo root when starting via ``start.sh`` / ``uvicorn`` from the repo). Pytest
and ad-hoc scripts that only import ``init_logger`` do not run that unless they call
``load_dotenv`` themselves.

Optional env (read in ``init_logger()``): ``INTY_LOGGING_LEVEL`` overrides YAML
``logging.level`` and applies to the file sink when ``INTY_LOG_FILE`` is set.
``INTY_CONSOLE_LOGGING_LEVEL`` overrides stderr only (omit to match ``INTY_LOGGING_LEVEL`` /
YAML). Use e.g. ``INTY_LOGGING_LEVEL=DEBUG`` + ``INTY_CONSOLE_LOGGING_LEVEL=INFO`` +
``INTY_LOG_FILE=...`` for DEBUG in file and INFO on terminal.
"""

import logging
import os
import sys
from pathlib import Path

from loguru import logger

from app.core.config import global_config_loaded_from_config_yaml
from app.utils.config import (
    LOGGING_FILE_FORMAT,
    LOGGING_LEVEL_FORMAT,
    LOGGING_MESSAGE_FORMAT,
    LOGGING_TIME_FORMAT,
)

_INTY_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _patch_log_record_repo_relative_file(record: dict) -> None:
    """将源码位置写成相对仓库根目录的路径，便于本地日志阅读与分享。"""
    raw_path = record["file"].path
    try:
        rel = Path(raw_path).resolve().relative_to(_INTY_REPO_ROOT)
        record["extra"]["inty_rel_file"] = rel.as_posix()
    except (OSError, ValueError):
        record["extra"]["inty_rel_file"] = raw_path


class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_globals.get("__name__") == __name__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def init_logger():
    """初始化日志配置"""
    # 移除默认的处理器
    logger.remove()

    # 配置默认的 request_id，避免在非请求上下文中出错；
    # inty_rel_file 由 patcher 填充（与 LOGGING_FILE_FORMAT 中 {extra[inty_rel_file]} 对应）
    logger.configure(
        extra={"request_id": "-", "inty_rel_file": ""},
        patcher=_patch_log_record_repo_relative_file,
    )

    log_level = os.environ.get("INTY_LOGGING_LEVEL", "").strip()
    if not log_level:
        log_level = global_config_loaded_from_config_yaml.logging.level

    console_level = os.environ.get("INTY_CONSOLE_LOGGING_LEVEL", "").strip()
    if not console_level:
        console_level = log_level

    # 添加控制台输出；colorize=True 时格式中的 <level>/<green> 等标签才会变为 ANSI 颜色
    logger.add(
        sys.stderr,
        level=console_level,
        format=global_config_loaded_from_config_yaml.logging.format,
        # 不指定这个参数，也没影响命令行颜色输出，但是保险起见，就加上了
        colorize=global_config_loaded_from_config_yaml.logging.colorize,
    )

    log_file = os.environ.get("INTY_LOG_FILE", "").strip()
    if log_file:
        file_format = (
            f"{LOGGING_TIME_FORMAT} | {LOGGING_LEVEL_FORMAT} | "
            f"{LOGGING_FILE_FORMAT} - {LOGGING_MESSAGE_FORMAT}"
        )
        logger.add(
            log_file,
            level=log_level,
            format=file_format,
            encoding="utf-8",
            colorize=False,
            enqueue=True,
        )

    # 拦截标准 logging 的日志（例如 FastAPI/uvicorn）
    intercept_handler = InterceptHandler()
    logging.basicConfig(handlers=[intercept_handler], level=0, force=True)

    # 指定要被接管的标准 logger 名称
    for name in (
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "fastapi",
        "gunicorn",
        "gunicorn.error",
    ):
        logging.getLogger(name).handlers = [intercept_handler]
        logging.getLogger(name).propagate = False

    # 抑制 google-genai SDK 的 WebSocket DEBUG 日志
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("websockets.client").setLevel(logging.WARNING)
    logging.getLogger("websockets.protocol").setLevel(logging.WARNING)
    # 抑制 OpenAI/httpx 调试日志，避免将 request payload（含聊天内容）写入日志
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("openai._base_client").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # LangSmith：set_langsmith_environment_variables 在 import app.core.config 时已执行，
    # 那会早于本函数，早先的 logger.debug 往往进不了文件 sink；这里再打一条便于确认是否开启。
    _raw = (os.environ.get("LANGSMITH_TRACING_V2") or "").strip().lower()
    _tracing_on = _raw in ("1", "true", "yes", "on")
    _project = os.environ.get("LANGSMITH_PROJECT", "")
    _key_set = bool((os.environ.get("LANGCHAIN_API_KEY") or "").strip())
    logger.info(
        "LangSmith: tracing_v2={} (env LANGSMITH_TRACING_V2={!r}), project={!r}, api_key_set={}",
        "on" if _tracing_on else "off",
        os.environ.get("LANGSMITH_TRACING_V2"),
        _project,
        _key_set,
    )
    logger.debug(
        "LangSmith: full env check LANGSMITH_TRACING_V2={!r} LANGSMITH_PROJECT={!r} LANGCHAIN_API_KEY_set={}",
        os.environ.get("LANGSMITH_TRACING_V2"),
        os.environ.get("LANGSMITH_PROJECT"),
        _key_set,
    )
