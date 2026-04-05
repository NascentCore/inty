"""REPL 空闲心跳：按 transcript 时间间隔估算「聊天节奏」，决定何时可触发一轮主动开口。"""

from __future__ import annotations

import os
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.agentic_kernel.companion.heartbeat import HEARTBEAT_SYNTHETIC_USER_TEXT  # noqa: F401

from .models import (
    ChatMessage,
    is_transcript_real_user_message,
    is_transcript_user_reengagement_after_heartbeat,
    load_transcript,
    transcript_without_trailing_presence_signals,
)
from .paths import WorkspacePaths

_DEFAULT_BASE_IDLE_SEC = 300.0
_DEFAULT_MIN_GAP_SEC = 1800.0
_DEFAULT_MIN_USER_QUIET_SEC = 240.0
_DEFAULT_MIN_TRANSCRIPT_LINES = 2

# REPL 单次 queue 等待上限，避免超大值导致长时间不响应环境变化
HEARTBEAT_MAX_SLEEP_CHUNK_SEC = 3600.0
_RHYTHM_CLAMP_SEC = (30.0, 900.0)


def heartbeat_enabled_from_env() -> bool:
    """
    未设置 `INTY_V2_PROTO_HEARTBEAT` 时默认 **开启**（本地 REPL 预期有空闲陪伴心跳）。
    显式关闭：`0` / `false` / `no` / `off`（与 `env_util.env_flag_enabled` 的 truthy 一致）。
    """
    raw = os.environ.get("INTY_V2_PROTO_HEARTBEAT")
    if raw is None or not str(raw).strip():
        return True
    s = str(raw).strip().lower()
    if s in ("0", "false", "no", "off"):
        return False
    return s in ("1", "true", "yes", "on")


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return float(str(raw).strip())


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return int(str(raw).strip())


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
        if not is_transcript_real_user_message(m):
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


def _rhythm_idle_seconds(msgs: list[ChatMessage]) -> float:
    base = _env_float("INTY_V2_PROTO_HEARTBEAT_IDLE_SEC", _DEFAULT_BASE_IDLE_SEC)
    gaps = _user_message_gaps_seconds(msgs)
    if len(gaps) < 2:
        return base
    med = float(statistics.median(gaps))
    # 用户回复越快，心跳可略早；越慢则拉长等待
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
        if is_transcript_real_user_message(m):
            return _parse_ts(m.ts)
    return None


def _has_reengagement_after_last_heartbeat(msgs: list[ChatMessage]) -> bool:
    hb_idx: int | None = None
    for i in range(len(msgs) - 1, -1, -1):
        m = msgs[i]
        if m.role == "user" and m.heartbeat is True:
            hb_idx = i
            break
    if hb_idx is None:
        return True
    for m in msgs[hb_idx + 1 :]:
        if is_transcript_user_reengagement_after_heartbeat(m):
            return True
    return False


def next_heartbeat_wait_seconds(
    workspace: Path,
    *,
    now: datetime | None = None,
    heartbeat_enabled: bool | None = None,
) -> float:
    """
    返回距离「允许触发心跳」的剩余秒数；已可触发时返回 <= 0。
    不满足前置条件（未启用、transcript 过短等）时返回大值，表示长时间不必再检查。

    `heartbeat_enabled`: 为 None 时与 REPL 一致，读 `INTY_V2_PROTO_HEARTBEAT`（`heartbeat_enabled_from_env`）；
    单测与脚本可显式传入 True/False 覆盖。
    """
    if heartbeat_enabled is False:
        return 86400.0 * 365.0
    if heartbeat_enabled is None and not heartbeat_enabled_from_env():
        return 86400.0 * 365.0

    root = workspace.resolve()
    paths = WorkspacePaths(root=root)
    msgs = load_transcript(paths.transcript)
    msgs_eff = transcript_without_trailing_presence_signals(msgs)
    min_lines = _env_int(
        "INTY_V2_PROTO_HEARTBEAT_MIN_TRANSCRIPT_MSGS",
        _DEFAULT_MIN_TRANSCRIPT_LINES,
    )
    if len(msgs_eff) < min_lines:
        return 86400.0 * 365.0

    if not msgs_eff or msgs_eff[-1].role != "assistant":
        return 86400.0 * 365.0

    last_asst = _last_assistant_ts(msgs_eff)
    if last_asst is None:
        return 86400.0 * 365.0

    # 用户离线期间，最多只允许一次心跳；须有一次「重新参与」（键入或 REPL 上线/会话恢复）后才允许下一次。
    if not _has_reengagement_after_last_heartbeat(msgs):
        return 86400.0 * 365.0

    t = now if now is not None else datetime.now(timezone.utc)
    rhythm = _rhythm_idle_seconds(msgs_eff)
    earliest = last_asst + timedelta(seconds=rhythm)

    min_user_quiet = _env_float(
        "INTY_V2_PROTO_HEARTBEAT_MIN_USER_QUIET_SEC",
        _DEFAULT_MIN_USER_QUIET_SEC,
    )
    last_real_user = _last_real_user_ts(msgs)
    if last_real_user is not None:
        user_quiet_earliest = last_real_user + timedelta(seconds=min_user_quiet)
        if user_quiet_earliest > earliest:
            earliest = user_quiet_earliest

    min_gap = _env_float("INTY_V2_PROTO_HEARTBEAT_MIN_GAP_SEC", _DEFAULT_MIN_GAP_SEC)
    last_hb = _last_heartbeat_user_ts(msgs)
    if last_hb is not None:
        hb_earliest = last_hb + timedelta(seconds=min_gap)
        if hb_earliest > earliest:
            earliest = hb_earliest

    remain = (earliest - t).total_seconds()
    return remain
