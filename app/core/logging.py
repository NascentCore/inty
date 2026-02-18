"""
init_logger() should be called at the very beginning of the application.
Afterwards, one should just use loguru.logger in the code:

```python
from loguru import logger

def your_function():
    logger.info("Hello, world!")
```
"""

import logging
import os
import sys
import time

from loguru import logger

from app.core.config import global_config_loaded_from_config_yaml


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

    # 添加控制台输出
    log_cfg = global_config_loaded_from_config_yaml.logging
    if log_cfg.json:
        # JSON 行格式：每行一个 JSON 对象，便于日志聚合/解析；serialize=True 时 format/colorize 被忽略
        logger.add(
            sys.stderr,
            level=log_cfg.level,
            serialize=True,
        )
    else:
        # 人类可读格式；colorize=True 时格式中的 <level>/<green> 等标签才会变为 ANSI 颜色
        logger.add(
            sys.stderr,
            level=log_cfg.level,
            format=log_cfg.format,
            colorize=log_cfg.colorize,
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
