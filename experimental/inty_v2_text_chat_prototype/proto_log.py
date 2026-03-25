"""loguru：stderr + 可选 workspace 下的 inty_v2.log（与 llm_trace.jsonl 并列，记运行时日志）。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from loguru import logger

_CONFIGURED = False


def configure_proto_log(log_file: Path | None, *, stderr_level: str = "INFO") -> None:
    """
    配置全局 loguru：始终有 stderr；若 log_file 非 None 则追加文件（enqueue 线程安全）。
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
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<level>{message}</level>"
        ),
    )
    if log_file is not None:
        path = log_file.resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            path,
            level="DEBUG",
            rotation="20 MB",
            retention="1 week",
            encoding="utf-8",
            enqueue=True,
            format=(
                "{time:YYYY-MM-DD HH:mm:ss.SSSZZ} | {level: <8} | "
                "{name}:{function}:{line} | {message}"
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
