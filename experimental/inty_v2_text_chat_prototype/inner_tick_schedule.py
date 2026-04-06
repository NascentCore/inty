"""REPL 空闲「内在节拍」：固定节奏 + 最小间隔，替代 transcript 节奏启发式。"""

from __future__ import annotations

import os
import time
from pathlib import Path

from .models import load_transcript, transcript_without_trailing_presence_signals
from .paths import WorkspacePaths

# `main` 中 `select` 等待 stdin / schedule 的单次睡眠上限（秒）
REPL_IDLE_MAX_SLEEP_CHUNK_SEC = 3600.0

# 开关关闭时返回该值，主循环几乎不因 inner tick 单独醒来
_DISABLED_INNER_TICK_WAIT_SEC = 86400.0 * 365.0

# transcript 未满足「可接话」前置时，单次等待不超过该秒数，避免久等后用户已多轮发言仍不重新判定
_INNER_TICK_BLOCKED_MAX_SLEEP_SEC = 60.0

_DEFAULT_INNER_TICK_SEC = 90.0
_DEFAULT_MIN_GAP_SEC = 120.0
_DEFAULT_MIN_TRANSCRIPT_MSGS = 2


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


def inner_tick_enabled_from_env() -> bool:
    """
    仅读 `INTY_V2_PROTO_INNER_TICK_ENABLED`：未设置或空则默认开启；`0`/`false`/`no`/`off` 关闭。
    """
    raw = os.environ.get("INTY_V2_PROTO_INNER_TICK_ENABLED")
    if raw is None or not str(raw).strip():
        return True
    s = str(raw).strip().lower()
    if s in ("0", "false", "no", "off"):
        return False
    return True


def inner_tick_poll_seconds() -> float:
    """空闲时多久醒来检查一次 stdin / 是否可触发内在节拍（上限块）。"""
    return _env_float("INTY_V2_PROTO_INNER_TICK_SEC", _DEFAULT_INNER_TICK_SEC)


def inner_tick_min_gap_seconds() -> float:
    """两次成功写入 transcript 的内在节拍回合之间的最小间隔（秒）。"""
    return _env_float("INTY_V2_PROTO_INNER_TICK_MIN_GAP_SEC", _DEFAULT_MIN_GAP_SEC)


def next_inner_tick_wait_seconds(
    workspace: Path,
    *,
    last_inner_fire_monotonic: float | None,
    now_monotonic: float | None = None,
) -> float:
    """
    距离「允许触发内在节拍」的剩余秒数；已可触发时返回 <= 0。

    - 未启用：返回超大值（主循环几乎不因 inner tick 醒来）。
    - transcript 行数不足或末条非 assistant：返回至多 `_INNER_TICK_BLOCKED_MAX_SLEEP_SEC`
      与 poll 上限的较小值，便于尽快重判。
    - `last_inner_fire_monotonic is None` 且上述前置已满足：视为本 REPL 会话尚未成功触发过
      inner tick，返回 0（与 `main` 在启用 inner tick 时以 `time.monotonic()` 初始化
      `last_inner_fire_mono` 的常见路径不同；供启动日志、单测或省略初始化的调用方使用）。
    - 否则按 `INTY_V2_PROTO_INNER_TICK_MIN_GAP_SEC` 相对上次触发的单调时钟计算剩余时间，
      并以 poll 上限封顶单次返回值。
    """
    if not inner_tick_enabled_from_env():
        return _DISABLED_INNER_TICK_WAIT_SEC

    now = now_monotonic if now_monotonic is not None else time.monotonic()
    root = workspace.resolve()
    paths = WorkspacePaths(root=root)
    msgs = transcript_without_trailing_presence_signals(
        load_transcript(paths.transcript)
    )
    min_lines = _env_int(
        "INTY_V2_PROTO_INNER_TICK_MIN_TRANSCRIPT_MSGS",
        _DEFAULT_MIN_TRANSCRIPT_MSGS,
    )
    poll = inner_tick_poll_seconds()
    blocked_sleep = min(_INNER_TICK_BLOCKED_MAX_SLEEP_SEC, poll)
    if len(msgs) < min_lines:
        return blocked_sleep

    if not msgs or msgs[-1].role != "assistant":
        return blocked_sleep

    min_gap = inner_tick_min_gap_seconds()
    if last_inner_fire_monotonic is None:
        return 0.0
    elapsed = now - last_inner_fire_monotonic
    remain = min_gap - elapsed
    if remain <= 0.0:
        return 0.0
    return min(remain, poll)
