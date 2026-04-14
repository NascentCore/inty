"""loguru：默认仅写 workspace 下 inty_v2.log（不污染 REPL 的 stderr）；关闭文件时退回 stderr。"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from loguru import logger

_CONFIGURED = False

# 文件 sink 默认 DEBUG；可用 INTY_V2_PROTO_LOG_FILE_LEVEL=INFO 等降低噪声（仍保留 INFO 及以上）。
_FILE_LEVEL = (
    os.getenv("INTY_V2_PROTO_LOG_FILE_LEVEL", "DEBUG").strip().upper() or "DEBUG"
)

# 与 app.utils.config.LOGGING_TIME_FORMAT 中 ZZ 一致，便于与 REPL 横幅对齐
_PROTO_TIME = "{time:YYYY-MM-DD HH:mm:ss.SSS ZZ}"


def repl_wall_ts_str() -> str:
    """本地墙钟时间字符串，与 proto log / 后端 LOGGING_TIME_FORMAT（ZZ）一致。"""
    dt = datetime.now().astimezone()
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + dt.strftime(" %z")


def configure_proto_log(log_file: Path | None, *, stderr_level: str = "INFO") -> None:
    """
    配置全局 loguru：
    - log_file 非 None：只写文件（enqueue 线程安全），不写 stderr，避免干扰 REPL。
    - log_file 为 None（--no-log-file 等）：只写 stderr。
    幂等：仅第一次调用生效，避免重复 add。
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True
    logger.remove()
    if log_file is not None:
        path = log_file.resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            path,
            level=_FILE_LEVEL,
            rotation="20 MB",
            retention="1 week",
            encoding="utf-8",
            enqueue=True,
            format=(
                _PROTO_TIME + " | {level: <8} | {name}:{function}:{line} | {message}"
            ),
        )
    else:
        logger.add(
            sys.stderr,
            level=stderr_level,
            format=(
                "<green>"
                + _PROTO_TIME
                + "</green> | <level>{level: <8}</level> | <level>{message}</level>"
            ),
        )


def resolve_proto_log_file(
    workspace: Path,
    *,
    explicit: Path | None,
    no_log_file: bool,
) -> Path | None:
    """
    解析文件日志路径。
    - --no-log-file：不写文件
    - --log-file PATH：显式路径
    - INTY_V2_PROTO_LOG_FILE：0/false/no/none 关闭；否则为路径字符串
    - 默认：<workspace>/inty_v2.log
    """
    if no_log_file:
        return None
    if explicit is not None:
        return explicit
    raw = os.getenv("INTY_V2_PROTO_LOG_FILE", "").strip()
    if raw.lower() in ("0", "false", "no", "none"):
        return None
    if raw:
        return Path(raw).expanduser()
    return workspace.resolve() / "inty_v2.log"
