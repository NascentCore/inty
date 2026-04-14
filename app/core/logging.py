"""
init_logger() should be called at the very beginning of the application.
Afterwards, one should just use loguru.logger in the code:

```python
from loguru import logger

def your_function():
    logger.info("Hello, world!")
```

Optional env (read in ``init_logger()``): ``INTY_LOGGING_LEVEL`` overrides YAML
``logging.level``; ``INTY_LOG_FILE`` appends a plain-text file sink (UTF-8, enqueue).
"""

import logging
import os
import sys
import time

from loguru import logger

from app.core.config import global_config_loaded_from_config_yaml
from app.utils.config import (
    LOGGING_FILE_FORMAT,
    LOGGING_LEVEL_FORMAT,
    LOGGING_MESSAGE_FORMAT,
    LOGGING_TIME_FORMAT,
)


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
    # 强制使用 UTC 时区，确保所有日志时间为 UTC
    os.environ["TZ"] = "UTC"
    time.tzset()
    # 移除默认的处理器
    logger.remove()

    # 配置默认的 request_id，避免在非请求上下文中出错
    logger.configure(extra={"request_id": "-"})

    log_level = os.environ.get("INTY_LOGGING_LEVEL", "").strip()
    if not log_level:
        log_level = global_config_loaded_from_config_yaml.logging.level

    # 添加控制台输出；colorize=True 时格式中的 <level>/<green> 等标签才会变为 ANSI 颜色
    logger.add(
        sys.stderr,
        level=log_level,
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
