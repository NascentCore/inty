"""用户本地钟上的「昼夜」划分：用于陪伴侧调度（夜间抑制主动心跳等）。

边界与 ``ImplicitSignalBundle.client_time`` / HTTP ``user_time_context`` 对齐；
无时区信息时视为白昼（不抑制），避免误伤未上报时间的客户端。
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Mapping

from pydantic import BaseModel


class AgentCircadianPhase(StrEnum):
    """粗粒度昼夜：仅影响默认调度策略，不写入人设文档。"""

    DAY = "day"
    NIGHT = "night"


class CircadianWindow(BaseModel):
    """本地 wall-clock 上「夜间」区间 [night_start, night_end)，跨午夜则用两段并集。"""

    night_start_hour: int = 22
    night_end_hour: int = 7


def _parse_iso_local_datetime(local_time: str) -> datetime | None:
    raw = (local_time or "").strip()
    if not raw:
        return None
    normalized = raw.replace("Z", "+00:00", 1) if raw.endswith("Z") else raw
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def local_datetime_from_user_time_context(
    ctx: Mapping[str, Any] | None,
) -> datetime | None:
    """从 ``UserTimeContext`` 风格 dict 取 ``local_time``；无时区则仍返回 naive/local 解析结果。"""
    if not ctx:
        return None
    lt = ctx.get("local_time")
    if not isinstance(lt, str):
        return None
    return _parse_iso_local_datetime(lt)


def agent_circadian_phase(
    ctx: Mapping[str, Any] | None,
    *,
    window: CircadianWindow | None = None,
) -> AgentCircadianPhase:
    """由用户本地钟推断昼夜；无法解析或缺字段时返回 ``DAY``。"""
    w = window or CircadianWindow()
    dt = local_datetime_from_user_time_context(ctx)
    if dt is None:
        return AgentCircadianPhase.DAY
    h = dt.hour
    start = w.night_start_hour % 24
    end = w.night_end_hour % 24
    if start == end:
        return AgentCircadianPhase.DAY
    if start > end:
        if h >= start or h < end:
            return AgentCircadianPhase.NIGHT
        return AgentCircadianPhase.DAY
    if start <= h < end:
        return AgentCircadianPhase.NIGHT
    return AgentCircadianPhase.DAY


def suppress_proactive_heartbeat_for_circadian(
    ctx: Mapping[str, Any] | None,
    *,
    window: CircadianWindow | None = None,
) -> bool:
    """夜间且能解析本地钟时为 True：应跳过主动心跳调度。"""
    return agent_circadian_phase(ctx, window=window) == AgentCircadianPhase.NIGHT
