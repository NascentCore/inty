"""陪伴侧「安静多久可以主动开口」的调度与文案素材。

- **调度**：依据 transcript 里用户消息间隔估计对话节奏，再结合配置（基准安静时长、两次心跳最短间隔、最少 transcript 行数等）计算 ``next_heartbeat_wait_seconds``；不满足前置条件时等价于「暂不开口」。
- **文案常量**：为主动心跳回合提供 system 侧约束与 user 占位（满足多轮 chat 形态）；占位正文的主路径在 turn 管线里按时间与 transcript 生成，本模块内的字面常量仅作回退。
- **与回合执行的关系**：真正触发 LLM 时使用内层 tick、``InnerTickMode.PROACTIVE_CHAT``；transcript 对用户占位行打 ``heartbeat`` 标记，供 ``min_gap_sec``（锚上一次心跳 user）与占位文案（如 ``build_proactive_heartbeat_transcript_user_marker``）区分合成 user 与真人 user。具体注入顺序见 companion turn 管线实现。
"""

from __future__ import annotations

import statistics
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, Field

from app.core.companion_harness.memory.memory_store import MemoryStore
from .models import ChatMessage, load_transcript_from_store

# 主动心跳回合里追加为 **system**：约束模型在用户未发新消息时如何接话（延续场景、禁工具、禁元话语）。
HEARTBEAT_SYNTHETIC_SYSTEM_MESSAGE = (
    "## Proactive Messaging (Heartbeat)\n"
    "- The user has not sent a new message for some time.\n"
    "- Based on the conversation context, your character's personality, and the time elapsed, decide whether to proactively send a message.\n"
    "- If you have something meaningful, respond appropriately.\n"
    "- If there is nothing appropriate to say right now, respond with exactly: [SILENT]\n"
)

# 主动心跳回退文案：当调用方拿不到 ``CompanionTurnResult.transcript_user_content`` 等内核结果时使用；主路径用 ``build_proactive_heartbeat_transcript_user_marker``。
PROACTIVE_HEARTBEAT_TRANSCRIPT_USER_MARKER = "[SYSTEM HEARTBEAT] The user has not sent a new message for some time."

_NEVER = 86400.0 * 365.0
_RHYTHM_CLAMP_SEC = (90.0, 900.0)


class HeartbeatConfig(BaseModel):
    """陪伴心跳调参：各字段 ``description`` 描述对用户侧体验的含义，不涉及调度实现。"""

    enabled: bool = Field(
        default=True,
        description=(
            "总开关。关则 companion 不会通过「心跳」这条路径在用户未发新消息时主动开口。"
        ),
    )
    base_idle_sec: float = Field(
        default=30.0,
        description=(
            "以助手上一轮**非心跳**回复说完为参照的「安静多久再开口」基准，刻画正常对话节拍下 "
            "companion 接话的松紧（对话还薄时更有感）；**不**针对「上一次是否已是心跳」单独计时。"
        ),
    )
    min_gap_sec: float = Field(
        default=60.0,
        description=(
            "以**上一次心跳式主动开口**为参照的最短间隔，专治用户仍不回时 companion **连着**自言自语；"
            "与 ``base_idle_sec`` **计时起点不同**（后者锚助手尾句，前者锚上一次心跳），"
            "二者同时满足里**更晚**的那一刻才放行。"
        ),
    )
    # TODO(session): min_transcript_lines counts the full transcript; replace with session-scoped gating when modeled.
    min_transcript_lines: int = Field(
        default=0,
        description=(
            "对话记录至少要有多少行（包含 AI 和用户的消息），才考虑允许心跳开口；越大越倾向「先有几轮真实互动再主动」，"
            "越小（含 0）越不以此为门槛。"
        ),
    )


def _parse_ts(ts: str) -> datetime:
    s = ts.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _user_message_gaps_seconds(msgs: list[ChatMessage]) -> list[float]:
    user_ts: list[datetime] = []
    for m in msgs:
        if m.role != "user":
            continue
        user_ts.append(_parse_ts(m.ts))
    if len(user_ts) < 2:
        return []
    gaps: list[float] = []
    for i in range(1, len(user_ts)):
        delta = (user_ts[i] - user_ts[i - 1]).total_seconds()
        if delta > 0:
            gaps.append(delta)
    return gaps[-5:]


def _rhythm_idle_seconds(msgs: list[ChatMessage], base: float) -> float:
    gaps = _user_message_gaps_seconds(msgs)
    if len(gaps) < 2:
        return base
    med = float(statistics.median(gaps))
    scaled = med * 0.65 + 20.0
    lo, hi = _RHYTHM_CLAMP_SEC
    return max(lo, min(hi, min(base * 2.0, scaled)))


def _last_assistant_ts(msgs: list[ChatMessage]) -> datetime | None:
    for m in reversed(msgs):
        if m.role == "assistant":
            return _parse_ts(m.ts)
    return None


def _format_elapsed_since(seconds: float) -> str:
    s = max(0, int(round(seconds)))
    if s < 60:
        return f"{s}s"
    if s < 3600:
        m, sec = divmod(s, 60)
        return f"{m}m {sec}s" if sec else f"{m}m"
    h, rem = divmod(s, 3600)
    m = rem // 60
    return f"{h}h {m}m" if m else f"{h}h"


def _last_non_heartbeat_user_ts(msgs: list[ChatMessage]) -> datetime | None:
    for m in reversed(msgs):
        if m.role == "user" and m.heartbeat is not True:
            return _parse_ts(m.ts)
    return None


def build_proactive_heartbeat_transcript_user_marker(
    msgs: list[ChatMessage],
    *,
    now: datetime | None = None,
) -> str:
    """英文一行：前缀 + 距上次真人用户消息 + 距上次助手消息（供 proactive 末轮 user 占位与 transcript）。"""
    t = now if now is not None else datetime.now(timezone.utc)
    last_u = _last_non_heartbeat_user_ts(msgs)
    last_a = _last_assistant_ts(msgs)
    if last_u is None:
        u_seg = "Time since the user's last message: no prior non-heartbeat user message in transcript."
    else:
        u_seg = f"Time since the user's last message: {_format_elapsed_since((t - last_u).total_seconds())}."
    if last_a is None:
        a_seg = "Time since the assistant's last message: no prior assistant message in transcript."
    else:
        a_seg = f"Time since the assistant's last message: {_format_elapsed_since((t - last_a).total_seconds())}."
    return f"[SYSTEM HEARTBEAT] {u_seg} {a_seg}"


def _last_heartbeat_user_ts(msgs: list[ChatMessage]) -> datetime | None:
    for m in reversed(msgs):
        if m.role == "user" and m.heartbeat is True:
            return _parse_ts(m.ts)
    return None


def next_heartbeat_wait_seconds(
    store: MemoryStore,
    config: HeartbeatConfig,
    *,
    now: datetime | None = None,
) -> float:
    """
    返回距离「允许触发心跳」的剩余秒数；已可触发时返回 <= 0。
    不满足前置条件时返回大值。
    """
    if not config.enabled:
        return _NEVER

    msgs = load_transcript_from_store(store, "transcript.jsonl")
    if len(msgs) < config.min_transcript_lines:
        return _NEVER

    if not msgs or msgs[-1].role != "assistant":
        return _NEVER

    last_asst = _last_assistant_ts(msgs)
    if last_asst is None:
        return _NEVER

    t = now if now is not None else datetime.now(timezone.utc)
    rhythm = _rhythm_idle_seconds(msgs, config.base_idle_sec)
    earliest = last_asst + timedelta(seconds=rhythm)

    last_hb = _last_heartbeat_user_ts(msgs)
    if last_hb is not None:
        hb_earliest = last_hb + timedelta(seconds=config.min_gap_sec)
        if hb_earliest > earliest:
            earliest = hb_earliest

    return (earliest - t).total_seconds()
