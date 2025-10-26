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
import sys

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
# 移除默认的处理器
    logger.remove()
#配置默认的request_id，避免在非请求上下文中错误
    logger.configure(extra={"request_id": "-"})
#添加控制台输出
    logger.add(
        sys.stderr,
        format=global_config_loaded_from_config_yaml.logging.format,
        level=global_config_loaded_from_config_yaml.logging.level,
        colorize=False,  # Disable ANSI colors to prevent escape codes in logs
    )
# 拦截标准logging的日志（例如FastAPI/uvicorn）
    intercept_handler = InterceptHandler()
    logging.basicConfig(handlers=[intercept_handler], level=0, force=True)
# 指定要被接管的标准记录器名称
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
