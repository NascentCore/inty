"""Persistent schedule queue + non-LLM due-event kernel."""

from __future__ import annotations

import json
import queue
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from loguru import logger

from app.core.companion_harness.memory.memory_store import MemoryStore
from .utc import utc_iso_ts
from app.core.companion_harness.memory.memory_store_scope import DEFAULT_MEMORY_STORE_SCOPE_PATHS

ScheduleTaskStatus = Literal["pending", "fired"]


@dataclass(frozen=True)
class ScheduleDueEvent:
    scope_registry_key: str
    task_id: str
    task_text: str
    exec_time_utc: str
    emitted_at_utc: str


def scheduled_task_synthetic_user_text(
    *,
    task_text: str,
    exec_time_utc: str,
) -> str:
    return (
        "（定时提醒触发）到期时间(UTC)："
        + exec_time_utc
        + "；提醒事项："
        + task_text.strip()
        + "。请在当前对话语境下自然提醒用户，不要提系统、队列、线程或工具。"
    )


@dataclass(frozen=True)
class ScheduleTask:
    id: str
    exec_time_utc: str
    task_text: str
    status: ScheduleTaskStatus
    created_at_utc: str
    fired_at_utc: str | None = None
    attempts: int = 0
    next_retry_utc: str | None = None
    last_error: str | None = None

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> ScheduleTask:
        return ScheduleTask(
            id=str(raw["id"]),
            exec_time_utc=str(raw["exec_time_utc"]),
            task_text=str(raw["task_text"]),
            status=str(raw.get("status", "pending")),  # type: ignore[arg-type]
            created_at_utc=str(raw["created_at_utc"]),
            fired_at_utc=(
                str(raw["fired_at_utc"])
                if raw.get("fired_at_utc") is not None
                else None
            ),
            attempts=int(raw.get("attempts", 0)),
            next_retry_utc=(
                str(raw["next_retry_utc"])
                if raw.get("next_retry_utc") is not None
                else None
            ),
            last_error=(
                str(raw["last_error"]) if raw.get("last_error") is not None else None
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "exec_time_utc": self.exec_time_utc,
            "task_text": self.task_text,
            "status": self.status,
            "created_at_utc": self.created_at_utc,
            "fired_at_utc": self.fired_at_utc,
            "attempts": self.attempts,
            "next_retry_utc": self.next_retry_utc,
            "last_error": self.last_error,
        }


def _parse_utc_ts(ts: str) -> datetime:
    s = ts.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        raise ValueError("timestamp must include timezone offset or Z")
    return dt.astimezone(timezone.utc)


def _schedule_document_rel() -> str:
    return DEFAULT_MEMORY_STORE_SCOPE_PATHS.schedule_queue_json


def _legacy_list_item_to_task(raw: dict[str, Any]) -> ScheduleTask:
    created = raw.get("created_at_utc") or raw.get("created_at")
    if not created:
        created = utc_iso_ts()
    fired = raw.get("fired_at_utc") or raw.get("fired_at")
    return ScheduleTask(
        id=str(raw["id"]),
        exec_time_utc=str(raw["exec_time_utc"]),
        task_text=str(raw.get("task_text", "")),
        status=str(raw.get("status", "pending")),  # type: ignore[arg-type]
        created_at_utc=str(created),
        fired_at_utc=str(fired) if fired is not None else None,
        attempts=int(raw.get("attempts", 0)),
        next_retry_utc=(
            str(raw["next_retry_utc"])
            if raw.get("next_retry_utc") is not None
            else None
        ),
        last_error=(
            str(raw["last_error"]) if raw.get("last_error") is not None else None
        ),
    )


def _load_tasks(store: MemoryStore) -> list[ScheduleTask]:
    rel = _schedule_document_rel()
    raw_body = store.read_document_if_exists(rel)
    if raw_body is None or not raw_body.strip():
        return []
    loaded = json.loads(raw_body)
    if isinstance(loaded, list):
        out: list[ScheduleTask] = []
        for x in loaded:
            if isinstance(x, dict):
                out.append(_legacy_list_item_to_task(x))
        return out
    if not isinstance(loaded, dict):
        raise ValueError(
            "schedule tasks document must be a JSON object or legacy array"
        )
    raw_tasks = loaded.get("tasks", [])
    if not isinstance(raw_tasks, list):
        raise ValueError("schedule tasks: key 'tasks' must be an array")
    return [ScheduleTask.from_dict(x) for x in raw_tasks]


def _save_tasks(store: MemoryStore, tasks: list[ScheduleTask]) -> None:
    body = {"tasks": [t.to_dict() for t in tasks]}
    payload = json.dumps(body, ensure_ascii=False, indent=2) + "\n"
    rel = _schedule_document_rel()
    store.write_document(rel, payload)


def _retry_backoff_seconds(attempts: int) -> float:
    return float(min(300, 2 ** max(1, attempts)))


def _task_ready_at_utc(task: ScheduleTask) -> datetime:
    if task.next_retry_utc:
        retry_at = _parse_utc_ts(task.next_retry_utc)
    else:
        retry_at = _parse_utc_ts(task.exec_time_utc)
    exec_at = _parse_utc_ts(task.exec_time_utc)
    return max(exec_at, retry_at)


def _safe_task_ready_at_utc(store: MemoryStore, task: ScheduleTask) -> datetime | None:
    try:
        ready_at = _task_ready_at_utc(task)
        _clear_invalid_warned(store, task.id)
        return ready_at
    except ValueError as exc:
        if _mark_invalid_warned(store, task.id):
            logger.warning(
                "schedule_queue skip_invalid_task task_id={} error={}",
                task.id,
                str(exc),
            )
        return None


def _pick_next_due_task(
    store: MemoryStore,
    tasks: list[ScheduleTask],
    *,
    now: datetime,
    in_flight_ids: set[str],
) -> ScheduleTask | None:
    due: list[tuple[ScheduleTask, datetime]] = []
    for t in tasks:
        if t.status != "pending":
            continue
        if t.id in in_flight_ids:
            continue
        ready_at = _safe_task_ready_at_utc(store, t)
        if ready_at is None:
            continue
        if ready_at <= now:
            due.append((t, ready_at))
    if not due:
        return None
    return sorted(
        due,
        key=lambda x: (
            x[1],
            x[0].created_at_utc,
            x[0].id,
        ),
    )[
        0
    ][0]


def next_due_task_for_execution(store: MemoryStore) -> ScheduleTask | None:
    """Return the next pending task that is due now (UTC), or ``None``.

    Ordering matches :func:`_pick_next_due_task` with no in-flight ids: earliest
    ready time, then ``created_at_utc``, then ``id``. Used by WebSocket inner-tick
    to pull one reminder per poll without starting the unused scheduler thread.
    """
    now = datetime.now(timezone.utc)
    tasks = _load_tasks(store)
    return _pick_next_due_task(store, tasks, now=now, in_flight_ids=set())


def _seconds_until_next_pending_task(
    store: MemoryStore,
    tasks: list[ScheduleTask],
    *,
    now: datetime,
    in_flight_ids: set[str],
) -> float | None:
    waits: list[float] = []
    for t in tasks:
        if t.status != "pending":
            continue
        if t.id in in_flight_ids:
            continue
        ready_at = _safe_task_ready_at_utc(store, t)
        if ready_at is None:
            continue
        waits.append((ready_at - now).total_seconds())
    if not waits:
        return None
    return min(waits)


def add_schedule_task(
    store: MemoryStore,
    *,
    exec_time_utc: str,
    task_text: str,
) -> str:
    sk = store.scope.registry_key()
    exec_at = _parse_utc_ts(exec_time_utc)
    text = task_text.strip()
    if not text:
        raise ValueError("task_text must be non-empty")
    tasks = _load_tasks(store)
    item = ScheduleTask(
        id=str(uuid.uuid4()),
        exec_time_utc=exec_at.isoformat(),
        task_text=text,
        status="pending",
        created_at_utc=utc_iso_ts(),
    )
    tasks.append(item)
    _save_tasks(store, tasks)
    logger.info(
        "schedule_queue task_added scope={} task_id={} exec_time_utc={} text_chars={}",
        sk,
        item.id,
        item.exec_time_utc,
        len(item.task_text),
    )
    return item.id


def mark_task_fired(store: MemoryStore, task_id: str) -> bool:
    tasks = _load_tasks(store)
    changed = False
    out: list[ScheduleTask] = []
    for t in tasks:
        if t.id != task_id:
            out.append(t)
            continue
        out.append(
            ScheduleTask(
                id=t.id,
                exec_time_utc=t.exec_time_utc,
                task_text=t.task_text,
                status="fired",
                created_at_utc=t.created_at_utc,
                fired_at_utc=utc_iso_ts(),
                attempts=t.attempts,
                next_retry_utc=None,
                last_error=None,
            )
        )
        changed = True
    if changed:
        _save_tasks(store, out)
        _clear_in_flight(store, task_id)
    return changed


def mark_task_retry(store: MemoryStore, task_id: str, error_text: str) -> bool:
    tasks = _load_tasks(store)
    changed = False
    out: list[ScheduleTask] = []
    now = datetime.now(timezone.utc)
    for t in tasks:
        if t.id != task_id:
            out.append(t)
            continue
        attempts = t.attempts + 1
        retry_at = now + timedelta(seconds=_retry_backoff_seconds(attempts))
        out.append(
            ScheduleTask(
                id=t.id,
                exec_time_utc=t.exec_time_utc,
                task_text=t.task_text,
                status="pending",
                created_at_utc=t.created_at_utc,
                fired_at_utc=None,
                attempts=attempts,
                next_retry_utc=retry_at.isoformat(),
                last_error=error_text.strip()[:500],
            )
        )
        changed = True
    if changed:
        _save_tasks(store, out)
        _clear_in_flight(store, task_id)
    return changed


def get_due_tasks(store: MemoryStore) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    tasks = _load_tasks(store)
    due: list[dict[str, Any]] = []
    for t in tasks:
        if t.status != "pending":
            continue
        ready = _safe_task_ready_at_utc(store, t)
        if ready is None or ready > now:
            continue
        due.append(
            {
                "id": t.id,
                "exec_time_utc": t.exec_time_utc,
                "task_text": t.task_text,
                "status": t.status,
                "created_at_utc": t.created_at_utc,
            }
        )
    return due


_EVENTS_QUEUE: queue.Queue[ScheduleDueEvent] | None = None
_EVENTS_QUEUE_LOCK = threading.Lock()


def _events_queue() -> queue.Queue[ScheduleDueEvent]:
    global _EVENTS_QUEUE
    with _EVENTS_QUEUE_LOCK:
        if _EVENTS_QUEUE is None:
            _EVENTS_QUEUE = queue.Queue()
        return _EVENTS_QUEUE


def pop_due_task_events_nowait(*, scope_registry_key: str) -> list[ScheduleDueEvent]:
    want = scope_registry_key.strip()
    out: list[ScheduleDueEvent] = []
    parked: list[ScheduleDueEvent] = []
    q = _events_queue()
    while True:
        try:
            ev = q.get_nowait()
        except queue.Empty:
            break
        if ev.scope_registry_key == want:
            out.append(ev)
        else:
            parked.append(ev)
    for ev in parked:
        q.put(ev)
    return out


@dataclass
class _SchedulerRunner:
    store: MemoryStore
    scope_registry_key: str
    stop_flag: threading.Event
    thread: threading.Thread
    in_flight_ids: set[str]
    lock: threading.Lock


_RUNNERS: dict[str, _SchedulerRunner] = {}
_RUNNERS_LOCK = threading.Lock()
_INVALID_TASK_WARNED_KEYS: set[tuple[str, str]] = set()
_INVALID_TASK_WARNED_KEYS_LOCK = threading.Lock()


def _runner_for_store(store: MemoryStore) -> _SchedulerRunner | None:
    with _RUNNERS_LOCK:
        return _RUNNERS.get(store.scope.registry_key())


def _clear_in_flight(store: MemoryStore, task_id: str) -> None:
    runner = _runner_for_store(store)
    if runner is None:
        return
    with runner.lock:
        runner.in_flight_ids.discard(task_id)


def _mark_invalid_warned(store: MemoryStore, task_id: str) -> bool:
    key = (store.scope.registry_key(), task_id)
    with _INVALID_TASK_WARNED_KEYS_LOCK:
        if key in _INVALID_TASK_WARNED_KEYS:
            return False
        _INVALID_TASK_WARNED_KEYS.add(key)
        return True


def _clear_invalid_warned(store: MemoryStore, task_id: str) -> None:
    key = (store.scope.registry_key(), task_id)
    with _INVALID_TASK_WARNED_KEYS_LOCK:
        _INVALID_TASK_WARNED_KEYS.discard(key)


def _reconcile_invalid_warned(store: MemoryStore, tasks: list[ScheduleTask]) -> None:
    sk = store.scope.registry_key()
    live_ids = {t.id for t in tasks}
    with _INVALID_TASK_WARNED_KEYS_LOCK:
        stale = [
            k for k in _INVALID_TASK_WARNED_KEYS if k[0] == sk and k[1] not in live_ids
        ]
        for k in stale:
            _INVALID_TASK_WARNED_KEYS.discard(k)


def _scheduler_loop(store: MemoryStore, stop_flag: threading.Event) -> None:
    sk = store.scope.registry_key()
    logger.info("schedule_queue scheduler_start scope={}", sk)
    while not stop_flag.is_set():
        runner = _runner_for_store(store)
        if runner is not None:
            with runner.lock:
                in_flight = set(runner.in_flight_ids)
        else:
            in_flight = set()
        now = datetime.now(timezone.utc)
        try:
            tasks = _load_tasks(store)
        except Exception:
            logger.exception("schedule_queue load failed scope={}", sk)
            stop_flag.wait(timeout=1.0)
            continue
        _reconcile_invalid_warned(store, tasks)
        due = _pick_next_due_task(store, tasks, now=now, in_flight_ids=in_flight)
        if due is not None:
            if runner is not None:
                with runner.lock:
                    runner.in_flight_ids.add(due.id)
            _events_queue().put(
                ScheduleDueEvent(
                    scope_registry_key=sk,
                    task_id=due.id,
                    task_text=due.task_text,
                    exec_time_utc=due.exec_time_utc,
                    emitted_at_utc=utc_iso_ts(),
                )
            )
            logger.info(
                "schedule_queue due_emitted scope={} task_id={} exec_time_utc={}",
                sk,
                due.id,
                due.exec_time_utc,
            )
            continue
        wait = _seconds_until_next_pending_task(
            store,
            tasks,
            now=now,
            in_flight_ids=in_flight,
        )
        if wait is None:
            sleep_s = 1.0
        else:
            sleep_s = min(60.0, max(0.05, wait))
        stop_flag.wait(timeout=sleep_s)
    logger.info("schedule_queue scheduler_stop scope={}", sk)


def start_schedule_scheduler(store: MemoryStore) -> None:
    sk = store.scope.registry_key()
    with _RUNNERS_LOCK:
        existing = _RUNNERS.get(sk)
        if existing is not None and existing.thread.is_alive():
            return
        stop_flag = threading.Event()
        runner = _SchedulerRunner(
            store=store,
            scope_registry_key=sk,
            stop_flag=stop_flag,
            thread=threading.Thread(
                target=_scheduler_loop,
                name=f"companion-scheduler-{store.scope.chat_id}",
                args=(store, stop_flag),
                daemon=True,
            ),
            in_flight_ids=set(),
            lock=threading.Lock(),
        )
        _RUNNERS[sk] = runner
        runner.thread.start()


def stop_schedule_scheduler(store: MemoryStore) -> None:
    sk = store.scope.registry_key()
    with _RUNNERS_LOCK:
        runner = _RUNNERS.get(sk)
    if runner is None:
        return
    if not runner.thread.is_alive():
        with _RUNNERS_LOCK:
            current = _RUNNERS.get(sk)
            if current is runner:
                _RUNNERS.pop(sk, None)
        return
    runner.stop_flag.set()
    runner.thread.join(timeout=2.0)
    if runner.thread.is_alive():
        logger.warning("schedule_queue scheduler_join_timeout scope={}", sk)
        with _RUNNERS_LOCK:
            current = _RUNNERS.get(sk)
            if current is None:
                _RUNNERS[sk] = runner
        return
    with _RUNNERS_LOCK:
        current = _RUNNERS.get(sk)
        if current is runner:
            _RUNNERS.pop(sk, None)


def pending_task_count(store: MemoryStore) -> int:
    tasks = _load_tasks(store)
    return len([t for t in tasks if t.status == "pending"])


def next_due_wait_seconds(
    store: MemoryStore, *, now: datetime | None = None
) -> float | None:
    t = now if now is not None else datetime.now(timezone.utc)
    tasks = _load_tasks(store)
    _reconcile_invalid_warned(store, tasks)
    runner = _runner_for_store(store)
    if runner is None:
        in_flight: set[str] = set()
    else:
        with runner.lock:
            in_flight = set(runner.in_flight_ids)
    return _seconds_until_next_pending_task(
        store,
        tasks,
        now=t,
        in_flight_ids=in_flight,
    )
