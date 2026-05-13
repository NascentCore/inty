"""loguru：REPL 仅写 stderr。"""

from __future__ import annotations

import sys
from datetime import datetime

from loguru import logger

_CONFIGURED = False

# 与 app.utils.config.LOGGING_TIME_FORMAT 中 ZZ 一致，便于与 REPL 横幅对齐
_PROTO_TIME = "{time:YYYY-MM-DD HH:mm:ss.SSS ZZ}"


def repl_wall_ts_str() -> str:
    """本地墙钟时间字符串，与 proto log / 后端 LOGGING_TIME_FORMAT（ZZ）一致。"""
    dt = datetime.now().astimezone()
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + dt.strftime(" %z")


def configure_proto_log(*, stderr_level: str = "INFO") -> None:
    """
    配置全局 loguru：仅 stderr。
    幂等：仅第一次调用生效，避免重复 add。
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True
    logger.remove()
    logger.add(
        sys.stderr,
        level=stderr_level,
        format=(
            "<green>"
            + _PROTO_TIME
            + "</green> | <level>{level: <8}</level> | <level>{message}</level>"
        ),
    )
