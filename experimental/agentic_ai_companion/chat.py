"""入口与组装：环境加载、logger、常量，从各模块导入并组装。"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Annotated

import cyclopts
from dotenv import load_dotenv

from .memory_compaction import CompactionConfig, ConversationCompactor

# 尽早加载 .env（显式路径，避免工作目录影响）
_THIS_DIR = Path(__file__).resolve().parent
_ENV_PATH = _THIS_DIR / ".env"
assert _ENV_PATH.exists(), f"环境变量文件不存在: {_ENV_PATH}"

load_dotenv(_ENV_PATH)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
from loguru import logger as _real_logger

# #region agent log
import json as _dbg_json
import time as _dbg_time
import traceback as _dbg_tb

_DBG_LOG_PATH = (
    "/Users/yzhao/Workspace/NascentCore/inty/.cursor/debug-7eab40.log"
)


def _debug_loguru_sink(message):
    """自定义 loguru sink：写入调试日志，捕获 handler 内部异常。"""
    record = message.record
    try:
        formatted_str = str(message)
        _payload = {
            "sessionId": "7eab40",
            "hypothesisId": "H1-sink",
            "location": "chat.py:_debug_loguru_sink",
            "message": "sink_success",
            "data": {
                "level": record["level"].name,
                "func": record["function"],
                "line": record["line"],
                "name": record["module"],
                "msg_preview": str(record["message"])[:300],
                "has_braces": "{" in str(record["message"])
                or "}" in str(record["message"]),
            },
            "timestamp": int(_dbg_time.time() * 1000),
        }
        with open(_DBG_LOG_PATH, "a") as _f:
            _f.write(_dbg_json.dumps(_payload) + "\n")
    except Exception as _exc:
        _err_payload = {
            "sessionId": "7eab40",
            "hypothesisId": "H1-sink-error",
            "location": "chat.py:_debug_loguru_sink:except",
            "message": "sink_raised_exception",
            "data": {
                "exc_type": type(_exc).__name__,
                "exc_str": str(_exc)[:500],
                "traceback": _dbg_tb.format_exc()[:1500],
                "msg_raw": str(record.get("message", ""))[:200],
            },
            "timestamp": int(_dbg_time.time() * 1000),
        }
        with open(_DBG_LOG_PATH, "a") as _f:
            _f.write(_dbg_json.dumps(_err_payload) + "\n")


_real_logger.add(_debug_loguru_sink, level="DEBUG", format="{message}")
# #endregion


class _LoggerWrapper:
    """包装器：当 enabled=False 时所有 logger.* 调用不输出，用于 --debug=false 减少屏幕干扰。"""

    def __init__(self, real, enabled: bool = False) -> None:
        self._real = real
        self._enabled = enabled

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def _log(self, level: str, msg: str, *args, **kwargs) -> None:
        if self._enabled:
            formatted = msg % args if args else msg
            # #region agent log
            _has_braces = "{" in formatted or "}" in formatted
            _payload = {
                "sessionId": "7eab40",
                "hypothesisId": "H1-postfix",
                "location": "chat.py:_log",
                "message": "_log_call",
                "data": {
                    "level": level,
                    "has_braces": _has_braces,
                    "msg_len": len(formatted),
                    "msg_preview": formatted[:200],
                },
                "timestamp": int(_dbg_time.time() * 1000),
            }
            try:
                with open(_DBG_LOG_PATH, "a") as _f:
                    _f.write(_dbg_json.dumps(_payload) + "\n")
            except Exception:
                pass
            # #endregion
            safe = formatted.replace("{", "{{").replace("}", "}}")
            getattr(self._real.opt(depth=2), level)(safe)

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
            formatted = msg % args if args else msg
            safe = formatted.replace("{", "{{").replace("}", "}}")
            self._real.opt(depth=2).exception(safe)


logger: _LoggerWrapper = _LoggerWrapper(_real_logger, enabled=False)

assert os.getenv("OPENROUTER_API_KEY") is not None, "OPENROUTER_API_KEY 未设置"

from . import clients
from . import prompts
from . import tools
from .repl import run_repl

OPENROUTER_MODEL = "deepseek/deepseek-v3.2"
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
    return prompts.build_system_messages_openai(
        char_name, user_name, _logger=logger
    )


def _build_system_messages_heartbeat(char_name: str, user_name: str):
    return prompts.build_system_messages_openai(
        char_name, user_name, heartbeat_enabled=True, _logger=logger
    )


def _suppress_noisy_loggers() -> None:
    """非 debug 模式下静默第三方库的 INFO 日志。"""
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("google_genai").setLevel(logging.WARNING)


def main(
    debug: Annotated[
        bool,
        cyclopts.Parameter(
            name="--debug",
            help="开启时输出 logger 日志，默认关闭以减少屏幕干扰",
        ),
    ] = False,
    enable_memory_compaction: Annotated[
        bool,
        cyclopts.Parameter(
            name="--enable-memory-compaction",
            help="开启实验性的记忆压缩：超预算时将历史对话压缩为情节+语义快照",
        ),
    ] = False,
    memory_max_context_chars: Annotated[
        int,
        cyclopts.Parameter(
            name="--memory-max-context-chars",
            help="触发压缩的上下文字符预算（近似 token）",
        ),
    ] = 9000,
    memory_keep_recent_messages: Annotated[
        int,
        cyclopts.Parameter(
            name="--memory-keep-recent-messages",
            help="压缩时保留最近原始消息数量",
        ),
    ] = 18,
    memory_max_messages_per_episode: Annotated[
        int,
        cyclopts.Parameter(
            name="--memory-max-messages-per-episode",
            help="构建情节记忆时每个 episode 的最大消息数",
        ),
    ] = 8,
    heartbeat: Annotated[
        bool,
        cyclopts.Parameter(
            name="--heartbeat",
            help="启用 heartbeat 模式：Agent 在用户无输入时定期主动发消息",
        ),
    ] = False,
    heartbeat_interval: Annotated[
        float,
        cyclopts.Parameter(
            name="--heartbeat-interval",
            help="心跳间隔（秒），仅在 --heartbeat 模式下生效",
        ),
    ] = 120.0,
) -> None:
    logger.set_enabled(debug)
    if not debug:
        _suppress_noisy_loggers()

    memory_compactor = None
    if enable_memory_compaction:
        memory_config = CompactionConfig(
            max_context_chars=memory_max_context_chars,
            keep_recent_messages=memory_keep_recent_messages,
            max_messages_per_episode=memory_max_messages_per_episode,
            max_episodic_entries=80,
            max_semantic_entries=80,
            summary_max_chars=1200,
            retrieval_episode_count=4,
            retrieval_semantic_count=8,
            retrieval_open_loop_count=6,
        )
        memory_compactor = ConversationCompactor(config=memory_config)
        logger.info("已启用 memory compaction: %s", memory_config.model_dump())

    if heartbeat:
        import asyncio

        from .async_repl import run_async_repl
        from .heartbeat import HeartbeatConfig

        config = HeartbeatConfig(interval_seconds=heartbeat_interval)
        logger.info("入口 main() 调用 run_async_repl（heartbeat 模式）")
        asyncio.run(
            run_async_repl(
                char_name=CHAR_NAME,
                user_name=USER_NAME,
                model=OPENROUTER_MODEL,
                build_system_messages=_build_system_messages_heartbeat,
                create_openai_client=clients.create_openai_client,
                get_gemini_client=clients.get_gemini_client,
                tools=TOOLS,
                tool_executors=TOOL_EXECUTORS,
                tool_types=TOOL_TYPES,
                tool_context_types=TOOL_CONTEXT_TYPES,
                process_response_with_tools=tools.process_response_with_tools,
                logger=logger,
                heartbeat_config=config,
            )
        )
        logger.info("run_async_repl 已退出")
    else:
        logger.info("入口 main() 调用 run_repl（同步模式）")
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
            memory_compactor=memory_compactor,
        )
        logger.info("run_repl 已退出")
