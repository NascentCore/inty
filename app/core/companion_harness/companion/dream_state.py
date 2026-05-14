"""梦境回合（记忆巩固）的调度状态：持久化在 MemoryStore，供 WebSocket 内在节拍 worker 使用。

设计对齐「离线巩固」隐喻：主 transcript 有足够新互动、且距上次巩固超过冷却时间，
则下一次维护性 inner tick 升格为 ``InnerTickMode.DREAM``（专用 system 切片 + 放宽写路径）。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from pydantic import AwareDatetime, BaseModel, Field

from app.core.companion_harness.memory.memory_store import MemoryStore
from .models import load_transcript_from_store
from .sleep_state import record_inner_tick_quiet_hours_from_now

DREAM_STATE_RELATIVE_PATH = ".companion_dream_state.json"

_DEFAULT_MIN_HOURS_BETWEEN = 20.0
_DEFAULT_MIN_NEW_MAIN_USER_ROWS = 3


class CompanionDreamState(BaseModel):
    """JSON 真源：``DREAM_STATE_RELATIVE_PATH``。"""

    last_completed_at_utc: AwareDatetime | None = None
    main_transcript_user_rows_at_last: int = Field(
        default=0,
        ge=0,
        description="完成巩固后 snapshot：主 transcript 中非心跳 user 行计数。",
    )


def count_main_transcript_user_rows(store: MemoryStore) -> int:
    rows = load_transcript_from_store(store, "transcript.jsonl")
    n = 0
    for m in rows:
        if m.role != "user":
            continue
        if m.heartbeat is True:
            continue
        n += 1
    return n


def load_dream_state(store: MemoryStore) -> CompanionDreamState:
    raw = store.read_document_if_exists(DREAM_STATE_RELATIVE_PATH)
    if raw is None or not raw.strip():
        return CompanionDreamState()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError(f"{DREAM_STATE_RELATIVE_PATH}: root must be a JSON object")
    return CompanionDreamState.model_validate(data)


def record_companion_dream_cycle_completed(
    store: MemoryStore,
    *,
    inner_tick_quiet_hours: float | None = None,
) -> None:
    """巩固回合成功结束后调用：刷新冷却锚与 transcript 计数；可选写入静息窗。"""
    st = CompanionDreamState(
        last_completed_at_utc=datetime.now(timezone.utc).replace(microsecond=0),
        main_transcript_user_rows_at_last=count_main_transcript_user_rows(store),
    )
    store.write_document(
        DREAM_STATE_RELATIVE_PATH,
        json.dumps(st.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
    )
    if inner_tick_quiet_hours is not None:
        record_inner_tick_quiet_hours_from_now(store, inner_tick_quiet_hours)


def dream_inner_tick_due(
    store: MemoryStore,
    *,
    min_hours_between: float = _DEFAULT_MIN_HOURS_BETWEEN,
    min_new_main_user_rows: int = _DEFAULT_MIN_NEW_MAIN_USER_ROWS,
) -> bool:
    """与 Claude Auto Dream 类似的双门闩：时间冷却 + 主轨用户互动量。"""
    st = load_dream_state(store)
    now = datetime.now(timezone.utc)
    last = st.last_completed_at_utc
    if last is not None:
        if now - last < timedelta(hours=min_hours_between):
            return False
    cur_users = count_main_transcript_user_rows(store)
    delta = cur_users - int(st.main_transcript_user_rows_at_last)
    if last is None:
        return cur_users >= min_new_main_user_rows
    return delta >= min_new_main_user_rows
