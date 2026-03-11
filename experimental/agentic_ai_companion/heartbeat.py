"""Heartbeat 引擎：配置、状态跟踪、信号构建。

使 Agent 能够在用户无输入时定期"醒来"，根据上下文决定是否主动发消息，
模拟始终在线的效果。心跳信号以 [SYSTEM HEARTBEAT] 前缀注入到对话中，
LLM 回复 [SILENT] 表示无需主动发消息。
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict

SILENT_TOKEN = "[SILENT]"
HEARTBEAT_PREFIX = "[SYSTEM HEARTBEAT]"

# 指数退避参数：连续静默超过此阈值后开始延长间隔
BACKOFF_THRESHOLD = 3
BACKOFF_MULTIPLIER = 1.5
MAX_INTERVAL_MULTIPLIER = 8.0


class HeartbeatConfig(BaseModel):
    """心跳配置。"""

    model_config = ConfigDict(frozen=True)

    interval_seconds: float = 120.0
    max_consecutive_silent: int = 10


class HeartbeatState(BaseModel):
    """心跳运行时状态，可变。"""

    model_config = ConfigDict(frozen=False)

    last_user_message_time: float = 0.0
    last_heartbeat_time: float = 0.0
    consecutive_silent_count: int = 0
    total_heartbeat_count: int = 0

    def record_user_activity(self) -> None:
        """用户发送消息时调用：重置计时器和静默计数。"""
        self.last_user_message_time = time.monotonic()
        self.consecutive_silent_count = 0

    def record_heartbeat(self, was_silent: bool) -> None:
        """心跳 turn 完成后调用：更新计数。"""
        self.last_heartbeat_time = time.monotonic()
        self.total_heartbeat_count += 1
        if was_silent:
            self.consecutive_silent_count += 1
        else:
            self.consecutive_silent_count = 0

    def compute_next_interval(self, base_interval: float) -> float:
        """根据连续静默次数计算下一次心跳间隔（指数退避）。"""
        if self.consecutive_silent_count <= BACKOFF_THRESHOLD:
            return base_interval
        extra = self.consecutive_silent_count - BACKOFF_THRESHOLD
        multiplier = min(BACKOFF_MULTIPLIER**extra, MAX_INTERVAL_MULTIPLIER)
        return base_interval * multiplier

    def seconds_since_last_user_message(self) -> float:
        """距离用户上次消息过去的秒数。首次调用（未初始化时）返回 0。"""
        if self.last_user_message_time == 0.0:
            return 0.0
        return time.monotonic() - self.last_user_message_time


def _format_elapsed(seconds: float) -> str:
    """将秒数格式化为人类可读的英文时间描述。"""
    if seconds < 60:
        return f"{int(seconds)} seconds"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f} minutes"
    hours = minutes / 60
    return f"{hours:.1f} hours"


def _extract_last_user_content(messages: list[dict]) -> str | None:
    """从 messages 列表中提取最后一条 user 消息的内容（忽略心跳信号）。"""
    for msg in reversed(messages):
        if msg.get("role") != "user":
            continue
        content = (msg.get("content") or "").strip()
        if content.startswith(HEARTBEAT_PREFIX):
            continue
        return content
    return None


def build_heartbeat_signal(state: HeartbeatState, messages: list[dict]) -> str:
    """根据当前状态和对话历史构建心跳信号内容。

    仅包含上下文数据（时间、最后消息），不包含行为指令
    （行为指令已在 HEARTBEAT_SYSTEM_PROMPT 中定义，避免重复浪费 token）。
    """
    elapsed = state.seconds_since_last_user_message()
    elapsed_desc = _format_elapsed(elapsed)
    now_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    last_user_msg = _extract_last_user_content(messages)
    last_user_part = ""
    if last_user_msg:
        preview = last_user_msg[:120]
        if len(last_user_msg) > 120:
            preview += "..."
        last_user_part = f'\nUser\'s last message was: "{preview}"'

    return (
        f"{HEARTBEAT_PREFIX} {elapsed_desc} since user's last message. "
        f"Current time: {now_str}."
        f"{last_user_part}"
    )


def is_heartbeat_response_silent(response_content: str) -> bool:
    """判断 LLM 回复是否为静默（包含 SILENT_TOKEN 或内容为空）。"""
    text = (response_content or "").strip()
    if not text:
        return True
    return SILENT_TOKEN in text
