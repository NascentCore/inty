"""Persistent schedule queue + non-LLM due-event kernel."""

from __future__ import annotations

import json
import queue
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

from loguru import logger

from .memory_registry import get_memory_store
from .utc import utc_iso_ts
from .memory_store_scope import MemoryStoreScopePaths

ScheduleTaskStatus = Literal["pending", "fired"]


@dataclass(frozen=True)
class ScheduleDueEvent:
    workspace: Path
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


def _schedule_document_rel_path(root: Path) -> str:
    r = root.resolve()
    return MemoryStoreScopePaths(root=r).schedule_queue_json.relative_to(r).as_posix()


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


def _load_tasks(root: Path) -> list[ScheduleTask]:
    store = get_memory_store(root)
    rel = _schedule_document_rel_path(root)
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


def _save_tasks(root: Path, tasks: list[ScheduleTask]) -> None:
    body = {"tasks": [t.to_dict() for t in tasks]}
    payload = json.dumps(body, ensure_ascii=False, indent=2) + "\n"
    store = get_memory_store(root)
    rel = _schedule_document_rel_path(root)
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


def _safe_task_ready_at_utc(workspace: Path, task: ScheduleTask) -> datetime | None:
    try:
        ready_at = _task_ready_at_utc(task)
        _clear_invalid_warned(workspace, task.id)
        return ready_at
    except ValueError as exc:
        if _mark_invalid_warned(workspace, task.id):
            logger.warning(
                "schedule_queue skip_invalid_task task_id={} error={}",
                task.id,
                str(exc),
            )
        return None


def _pick_next_due_task(
    workspace: Path,
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
        ready_at = _safe_task_ready_at_utc(workspace, t)
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


def _seconds_until_next_pending_task(
    workspace: Path,
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
        ready_at = _safe_task_ready_at_utc(workspace, t)
        if ready_at is None:
            continue
        waits.append((ready_at - now).total_seconds())
    if not waits:
        return None
    return min(waits)


def add_schedule_task(
    root: Path,
    *,
    exec_time_utc: str,
    task_text: str,
) -> str:
    rt = root.resolve()
    exec_at = _parse_utc_ts(exec_time_utc)
    text = task_text.strip()
    if not text:
        raise ValueError("task_text must be non-empty")
    tasks = _load_tasks(rt)
    item = ScheduleTask(
        id=str(uuid.uuid4()),
        exec_time_utc=exec_at.isoformat(),
        task_text=text,
        status="pending",
        created_at_utc=utc_iso_ts(),
    )
    tasks.append(item)
    _save_tasks(rt, tasks)
    logger.info(
        "schedule_queue task_added ws={} task_id={} exec_time_utc={} text_chars={}",
        rt.name,
        item.id,
        item.exec_time_utc,
        len(item.task_text),
    )
    return item.id


def mark_task_fired(root: Path, task_id: str) -> bool:
    rt = root.resolve()
    tasks = _load_tasks(rt)
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
        _save_tasks(rt, out)
        _clear_in_flight(rt, task_id)
    return changed


def mark_task_retry(root: Path, task_id: str, error_text: str) -> bool:
    rt = root.resolve()
    tasks = _load_tasks(rt)
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
        _save_tasks(rt, out)
        _clear_in_flight(rt, task_id)
    return changed


def get_due_tasks(workspace: Path) -> list[dict[str, Any]]:
    root = workspace.resolve()
    now = datetime.now(timezone.utc)
    tasks = _load_tasks(root)
    due: list[dict[str, Any]] = []
    for t in tasks:
        if t.status != "pending":
            continue
        ready = _safe_task_ready_at_utc(root, t)
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


def pop_due_task_events_nowait(*, workspace: Path) -> list[ScheduleDueEvent]:
    root = workspace.resolve()
    out: list[ScheduleDueEvent] = []
    parked: list[ScheduleDueEvent] = []
    q = _events_queue()
    while True:
        try:
            ev = q.get_nowait()
        except queue.Empty:
            break
        if ev.workspace.resolve() == root:
            out.append(ev)
        else:
            parked.append(ev)
    for ev in parked:
        q.put(ev)
    return out


@dataclass
class _SchedulerRunner:
    workspace: Path
    stop_flag: threading.Event
    thread: threading.Thread
    in_flight_ids: set[str]
    lock: threading.Lock


_RUNNERS: dict[Path, _SchedulerRunner] = {}
_RUNNERS_LOCK = threading.Lock()
_INVALID_TASK_WARNED_KEYS: set[tuple[Path, str]] = set()
_INVALID_TASK_WARNED_KEYS_LOCK = threading.Lock()


def _runner_for(workspace: Path) -> _SchedulerRunner | None:
    with _RUNNERS_LOCK:
        return _RUNNERS.get(workspace.resolve())


def _clear_in_flight(workspace: Path, task_id: str) -> None:
    runner = _runner_for(workspace.resolve())
    if runner is None:
        return
    with runner.lock:
        runner.in_flight_ids.discard(task_id)


def _mark_invalid_warned(workspace: Path, task_id: str) -> bool:
    key = (workspace.resolve(), task_id)
    with _INVALID_TASK_WARNED_KEYS_LOCK:
        if key in _INVALID_TASK_WARNED_KEYS:
            return False
        _INVALID_TASK_WARNED_KEYS.add(key)
        return True


def _clear_invalid_warned(workspace: Path, task_id: str) -> None:
    key = (workspace.resolve(), task_id)
    with _INVALID_TASK_WARNED_KEYS_LOCK:
        _INVALID_TASK_WARNED_KEYS.discard(key)


def _reconcile_invalid_warned(workspace: Path, tasks: list[ScheduleTask]) -> None:
    root = workspace.resolve()
    live_ids = {t.id for t in tasks}
    with _INVALID_TASK_WARNED_KEYS_LOCK:
        stale = [
            k
            for k in _INVALID_TASK_WARNED_KEYS
            if k[0] == root and k[1] not in live_ids
        ]
        for k in stale:
            _INVALID_TASK_WARNED_KEYS.discard(k)


def _scheduler_loop(workspace: Path, stop_flag: threading.Event) -> None:
    root = workspace.resolve()
    logger.info("schedule_queue scheduler_start ws={}", root.name)
    while not stop_flag.is_set():
        runner = _runner_for(root)
        if runner is not None:
            with runner.lock:
                in_flight = set(runner.in_flight_ids)
        else:
            in_flight = set()
        now = datetime.now(timezone.utc)
        try:
            tasks = _load_tasks(root)
        except Exception:
            logger.exception("schedule_queue load failed ws={}", root.name)
            stop_flag.wait(timeout=1.0)
            continue
        _reconcile_invalid_warned(root, tasks)
        due = _pick_next_due_task(root, tasks, now=now, in_flight_ids=in_flight)
        if due is not None:
            if runner is not None:
                with runner.lock:
                    runner.in_flight_ids.add(due.id)
            _events_queue().put(
                ScheduleDueEvent(
                    workspace=root,
                    task_id=due.id,
                    task_text=due.task_text,
                    exec_time_utc=due.exec_time_utc,
                    emitted_at_utc=utc_iso_ts(),
                )
            )
            logger.info(
                "schedule_queue due_emitted ws={} task_id={} exec_time_utc={}",
                root.name,
                due.id,
                due.exec_time_utc,
            )
            continue
        wait = _seconds_until_next_pending_task(
            root,
            tasks,
            now=now,
            in_flight_ids=in_flight,
        )
        if wait is None:
            sleep_s = 1.0
        else:
            sleep_s = min(60.0, max(0.05, wait))
        stop_flag.wait(timeout=sleep_s)
    logger.info("schedule_queue scheduler_stop ws={}", root.name)


def start_schedule_scheduler(workspace: Path) -> None:
    root = workspace.resolve()
    with _RUNNERS_LOCK:
        existing = _RUNNERS.get(root)
        if existing is not None and existing.thread.is_alive():
            return
        stop_flag = threading.Event()
        runner = _SchedulerRunner(
            workspace=root,
            stop_flag=stop_flag,
            thread=threading.Thread(
                target=_scheduler_loop,
                name=f"companion-scheduler-{root.name}",
                args=(root, stop_flag),
                daemon=True,
            ),
            in_flight_ids=set(),
            lock=threading.Lock(),
        )
        _RUNNERS[root] = runner
        runner.thread.start()


def stop_schedule_scheduler(workspace: Path) -> None:
    root = workspace.resolve()
    with _RUNNERS_LOCK:
        runner = _RUNNERS.get(root)
    if runner is None:
        return
    if not runner.thread.is_alive():
        with _RUNNERS_LOCK:
            current = _RUNNERS.get(root)
            if current is runner:
                _RUNNERS.pop(root, None)
        return
    runner.stop_flag.set()
    runner.thread.join(timeout=2.0)
    if runner.thread.is_alive():
        logger.warning("schedule_queue scheduler_join_timeout ws={}", root.name)
        with _RUNNERS_LOCK:
            current = _RUNNERS.get(root)
            if current is None:
                _RUNNERS[root] = runner
        return
    with _RUNNERS_LOCK:
        current = _RUNNERS.get(root)
        if current is runner:
            _RUNNERS.pop(root, None)


def pending_task_count(workspace: Path) -> int:
    tasks = _load_tasks(workspace.resolve())
    return len([t for t in tasks if t.status == "pending"])


def next_due_wait_seconds(
    workspace: Path, *, now: datetime | None = None
) -> float | None:
    root = workspace.resolve()
    t = now if now is not None else datetime.now(timezone.utc)
    tasks = _load_tasks(root)
    _reconcile_invalid_warned(root, tasks)
    runner = _runner_for(root)
    if runner is None:
        in_flight: set[str] = set()
    else:
        with runner.lock:
            in_flight = set(runner.in_flight_ids)
    return _seconds_until_next_pending_task(
        root,
        tasks,
        now=t,
        in_flight_ids=in_flight,
    )
