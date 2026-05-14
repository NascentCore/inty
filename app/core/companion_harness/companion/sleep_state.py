"""维护性 inner tick 的「静息」与可附属的轻量创作片段计数（与昼夜判定配合）。

产品语义（与实现计划一致）：
- **静息起点**：一次成功的记忆巩固（``InnerTickMode.DREAM``）完成时，将
  ``inner_tick_quiet_until_utc`` 设为 ``now_utc + N 小时``（默认 3h，见配置）。
- **静息期内**：任何 WebSocket 维护性 inner tick **不调** ``run_companion_chat_turn``（零主轮 LLM），
  与夜间降频的 ``max(schedule_remain, quiet_remain)`` 合并等待。
- **白昼**：用户本地钟进入白昼时清空 ``inner_tick_quiet_until_utc``，避免静息跨日悬挂。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from pydantic import AwareDatetime, BaseModel, Field

from app.core.companion_harness.memory.memory_store import MemoryStore

SLEEP_STATE_RELATIVE_PATH = ".companion_sleep_state.json"


class CompanionSleepState(BaseModel):
    """JSON 真源：``SLEEP_STATE_RELATIVE_PATH``。"""

    inner_tick_quiet_until_utc: AwareDatetime | None = None
    creative_fragment_local_date: str | None = None
    creative_fragments_today: int = Field(default=0, ge=0)


def load_sleep_state(store: MemoryStore) -> CompanionSleepState:
    raw = store.read_document_if_exists(SLEEP_STATE_RELATIVE_PATH)
    if raw is None or not raw.strip():
        return CompanionSleepState()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError(f"{SLEEP_STATE_RELATIVE_PATH}: root must be a JSON object")
    return CompanionSleepState.model_validate(data)


def persist_sleep_state(store: MemoryStore, state: CompanionSleepState) -> None:
    store.write_document(
        SLEEP_STATE_RELATIVE_PATH,
        json.dumps(state.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
    )


def clear_inner_tick_quiet_if_circadian_day(store: MemoryStore, *, is_night: bool) -> None:
    """白昼时丢弃静_until；夜间不动。"""
    if is_night:
        return
    st = load_sleep_state(store)
    if st.inner_tick_quiet_until_utc is None:
        return
    persist_sleep_state(
        store, st.model_copy(update={"inner_tick_quiet_until_utc": None})
    )


def record_inner_tick_quiet_hours_from_now(store: MemoryStore, hours: float) -> None:
    if hours <= 0.0:
        return
    now = datetime.now(timezone.utc).replace(microsecond=0)
    until = (now + timedelta(hours=hours)).replace(microsecond=0)
    st = load_sleep_state(store)
    persist_sleep_state(
        store, st.model_copy(update={"inner_tick_quiet_until_utc": until})
    )


def inner_tick_quiet_remain_seconds(
    store: MemoryStore, *, now_utc: datetime | None = None
) -> float:
    st = load_sleep_state(store)
    until = st.inner_tick_quiet_until_utc
    if until is None:
        return 0.0
    now = now_utc or datetime.now(timezone.utc)
    if now.microsecond:
        now = now.replace(microsecond=0)
    if until.microsecond:
        until = until.replace(microsecond=0)
    if now >= until:
        return 0.0
    return max(0.0, (until - now).total_seconds())


def try_reserve_creative_fragment_slot(
    store: MemoryStore, *, local_date: str, max_per_day: int
) -> bool:
    """同一用户本地日内至多 ``max_per_day`` 条；成功则持久化递增并返回 True。"""
    if max_per_day <= 0:
        return False
    st = load_sleep_state(store)
    date_key = (local_date or "").strip()
    if not date_key:
        return False
    count = int(st.creative_fragments_today)
    if st.creative_fragment_local_date != date_key:
        count = 0
    if count >= max_per_day:
        return False
    persist_sleep_state(
        store,
        st.model_copy(
            update={
                "creative_fragment_local_date": date_key,
                "creative_fragments_today": count + 1,
            }
        ),
    )
    return True


def record_creative_fragment_written_failed_rollback(
    store: MemoryStore, *, local_date: str
) -> None:
    """若补全抛错，把当日计数减回（不减到负）。"""
    st = load_sleep_state(store)
    date_key = (local_date or "").strip()
    if not date_key or st.creative_fragment_local_date != date_key:
        return
    n = int(st.creative_fragments_today)
    if n <= 0:
        return
    persist_sleep_state(
        store, st.model_copy(update={"creative_fragments_today": n - 1})
    )
