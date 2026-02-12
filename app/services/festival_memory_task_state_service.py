"""Track festival-memory extraction run status in memory."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from threading import RLock
from typing import Dict, Optional

RUN_STATUS_IDLE = "idle"
RUN_STATUS_RUNNING = "running"
RUN_STATUS_COMPLETED = "completed"
RUN_STATUS_FAILED = "failed"


@dataclass
class FestivalMemoryTaskState:
    config_id: int
    festival_name: str
    festival_date: date
    run_status: str
    run_started_at: Optional[datetime] = None
    run_finished_at: Optional[datetime] = None
    run_total_pairs: Optional[int] = None
    run_success_count: Optional[int] = None
    run_failed_count: Optional[int] = None
    run_error_message: Optional[str] = None


_state_lock = RLock()
_states_by_config_id: Dict[int, FestivalMemoryTaskState] = {}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def clear_run_states() -> None:
    with _state_lock:
        _states_by_config_id.clear()


def mark_running(config_id: int, festival_name: str, festival_date: date) -> None:
    now = _utc_now()
    state = FestivalMemoryTaskState(
        config_id=config_id,
        festival_name=festival_name,
        festival_date=festival_date,
        run_status=RUN_STATUS_RUNNING,
        run_started_at=now,
        run_finished_at=None,
        run_total_pairs=None,
        run_success_count=None,
        run_failed_count=None,
        run_error_message=None,
    )
    with _state_lock:
        _states_by_config_id[config_id] = state


def mark_completed(
    config_id: int,
    festival_name: str,
    festival_date: date,
    *,
    total_pairs: int,
    success_count: int,
    failed_count: int,
) -> None:
    now = _utc_now()
    with _state_lock:
        previous = _states_by_config_id.get(config_id)
        run_started_at = (
            previous.run_started_at if previous and previous.run_started_at else now
        )
        _states_by_config_id[config_id] = FestivalMemoryTaskState(
            config_id=config_id,
            festival_name=festival_name,
            festival_date=festival_date,
            run_status=RUN_STATUS_COMPLETED,
            run_started_at=run_started_at,
            run_finished_at=now,
            run_total_pairs=total_pairs,
            run_success_count=success_count,
            run_failed_count=failed_count,
            run_error_message=None,
        )


def mark_failed(
    config_id: int,
    festival_name: str,
    festival_date: date,
    *,
    total_pairs: int,
    success_count: int,
    failed_count: int,
    error_message: Optional[str] = None,
) -> None:
    now = _utc_now()
    with _state_lock:
        previous = _states_by_config_id.get(config_id)
        run_started_at = (
            previous.run_started_at if previous and previous.run_started_at else now
        )
        _states_by_config_id[config_id] = FestivalMemoryTaskState(
            config_id=config_id,
            festival_name=festival_name,
            festival_date=festival_date,
            run_status=RUN_STATUS_FAILED,
            run_started_at=run_started_at,
            run_finished_at=now,
            run_total_pairs=total_pairs,
            run_success_count=success_count,
            run_failed_count=failed_count,
            run_error_message=error_message,
        )


def get_run_state(config_id: int) -> Optional[FestivalMemoryTaskState]:
    with _state_lock:
        state = _states_by_config_id.get(config_id)
        if state is None:
            return None
        return FestivalMemoryTaskState(
            config_id=state.config_id,
            festival_name=state.festival_name,
            festival_date=state.festival_date,
            run_status=state.run_status,
            run_started_at=state.run_started_at,
            run_finished_at=state.run_finished_at,
            run_total_pairs=state.run_total_pairs,
            run_success_count=state.run_success_count,
            run_failed_count=state.run_failed_count,
            run_error_message=state.run_error_message,
        )
