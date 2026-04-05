"""REPL 空闲「内在节拍」：固定节奏 + 最小间隔，替代 transcript 节奏启发式。"""

from __future__ import annotations

import os
import time
from pathlib import Path

from .models import load_transcript, transcript_without_trailing_presence_signals
from .paths import WorkspacePaths

# `main` 中 `select` 等待 stdin / schedule 的单次睡眠上限（秒）
REPL_IDLE_MAX_SLEEP_CHUNK_SEC = 3600.0

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
    未启用或 transcript 不满足前置时返回较大值（仍受主循环 poll 上限约束）。
    """
    if not inner_tick_enabled_from_env():
        return 86400.0 * 365.0

    now = now_monotonic if now_monotonic is not None else time.monotonic()
    root = workspace.resolve()
    paths = WorkspacePaths(root=root)
    msgs = transcript_without_trailing_presence_signals(load_transcript(paths.transcript))
    min_lines = _env_int(
        "INTY_V2_PROTO_INNER_TICK_MIN_TRANSCRIPT_MSGS",
        _DEFAULT_MIN_TRANSCRIPT_MSGS,
    )
    if len(msgs) < min_lines:
        return min(60.0, inner_tick_poll_seconds())

    if not msgs or msgs[-1].role != "assistant":
        return min(60.0, inner_tick_poll_seconds())

    min_gap = inner_tick_min_gap_seconds()
    if last_inner_fire_monotonic is None:
        return 0.0
    elapsed = now - last_inner_fire_monotonic
    remain = min_gap - elapsed
    if remain <= 0.0:
        return 0.0
    return min(remain, inner_tick_poll_seconds())
