"""陪伴心跳调度：按 transcript 时间间隔估算聊天节奏，决定何时可触发主动开口。

触发模型回合时，请使用 ``run_turn(..., inner_tick_turn=True,
inner_tick_mode=InnerTickMode.PROACTIVE_CHAT)``（与原 ``heartbeat_turn`` 等价语义：
``HEARTBEAT_SYNTHETIC_USER_TEXT`` + 无工具）；本模块保留时间与合成文案常量。
"""

from __future__ import annotations

import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from .memory_registry import get_memory_store
from .models import ChatMessage, load_transcript_from_store

HEARTBEAT_SYNTHETIC_USER_TEXT = (
    "（陪伴心跳：用户尚未输入新内容。请读本窗口里**正在进行的场景、话题与语气**，用一两句自然接话，"
    "延续当下氛围与节奏，像同一场对话的下一拍；不要突然换风格、换口吻或像新开一局；"
    "不要提系统、心跳、等待或「我以为你走了」；不要调用工具。）"
)

_NEVER = 86400.0 * 365.0
_RHYTHM_CLAMP_SEC = (90.0, 900.0)


class HeartbeatConfig(BaseModel):
    enabled: bool = False
    base_idle_sec: float = 300.0
    min_gap_sec: float = 1800.0
    min_user_quiet_sec: float = 240.0
    min_transcript_lines: int = 2


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


def _last_heartbeat_user_ts(msgs: list[ChatMessage]) -> datetime | None:
    for m in reversed(msgs):
        if m.role == "user" and m.heartbeat is True:
            return _parse_ts(m.ts)
    return None


def _last_real_user_ts(msgs: list[ChatMessage]) -> datetime | None:
    for m in reversed(msgs):
        if m.role == "user" and m.heartbeat is not True:
            return _parse_ts(m.ts)
    return None


def _has_real_user_after_last_heartbeat(msgs: list[ChatMessage]) -> bool:
    hb_idx: int | None = None
    for i in range(len(msgs) - 1, -1, -1):
        m = msgs[i]
        if m.role == "user" and m.heartbeat is True:
            hb_idx = i
            break
    if hb_idx is None:
        return True
    for m in msgs[hb_idx + 1 :]:
        if m.role == "user" and m.heartbeat is not True:
            return True
    return False


def next_heartbeat_wait_seconds(
    workspace: Path,
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

    root = workspace.resolve()
    store = get_memory_store(root)
    msgs = load_transcript_from_store(store, "transcript.jsonl")
    if len(msgs) < config.min_transcript_lines:
        return _NEVER

    if not msgs or msgs[-1].role != "assistant":
        return _NEVER

    last_asst = _last_assistant_ts(msgs)
    if last_asst is None:
        return _NEVER

    if not _has_real_user_after_last_heartbeat(msgs):
        return _NEVER

    t = now if now is not None else datetime.now(timezone.utc)
    rhythm = _rhythm_idle_seconds(msgs, config.base_idle_sec)
    earliest = last_asst + timedelta(seconds=rhythm)

    last_real_user = _last_real_user_ts(msgs)
    if last_real_user is not None:
        user_quiet_earliest = last_real_user + timedelta(
            seconds=config.min_user_quiet_sec
        )
        if user_quiet_earliest > earliest:
            earliest = user_quiet_earliest

    last_hb = _last_heartbeat_user_ts(msgs)
    if last_hb is not None:
        hb_earliest = last_hb + timedelta(seconds=config.min_gap_sec)
        if hb_earliest > earliest:
            earliest = hb_earliest

    return (earliest - t).total_seconds()
