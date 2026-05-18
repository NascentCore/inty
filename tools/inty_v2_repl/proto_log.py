"""loguru：REPL 仅写 stderr。"""

from __future__ import annotations

import sys
from datetime import datetime

from loguru import logger

_CONFIGURED = False

# REPL 终端展示：本地墙钟，精确到秒，不含时区偏移。
_PROTO_TIME = "{time:YYYY-MM-DD HH:mm:ss}"


def repl_wall_ts_str() -> str:
    """本地墙钟时间字符串，供 stdout 横幅与 stderr proto log 共用。"""
    dt = datetime.now().astimezone()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


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
