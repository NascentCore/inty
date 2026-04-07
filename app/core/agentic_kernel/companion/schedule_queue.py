"""定时任务队列：持久化到 .companion_schedule_tasks.json，后台线程轮询到期事件。"""

from __future__ import annotations

import json
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from loguru import logger

from .file_store import read_text, write_text
from .workspace import WorkspacePaths


def _load_tasks(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        data = json.loads(read_text(path))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return data


def _save_tasks(path: Path, tasks: list[dict[str, Any]]) -> None:
    write_text(path, json.dumps(tasks, ensure_ascii=False, indent=2) + "\n")


def add_schedule_task(
    workspace: Path,
    *,
    exec_time_utc: str,
    task_text: str,
) -> str:
    """写入一条定时任务。返回 task id。"""
    root = workspace.resolve()
    paths = WorkspacePaths(root=root)
    queue_path = paths.schedule_queue_json
    tasks = _load_tasks(queue_path)
    task_id = str(uuid.uuid4())
    tasks.append(
        {
            "id": task_id,
            "exec_time_utc": exec_time_utc,
            "task_text": task_text,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    _save_tasks(queue_path, tasks)
    logger.info("schedule_queue task_added id={} exec={}", task_id, exec_time_utc)
    return task_id


def get_due_tasks(workspace: Path) -> list[dict[str, Any]]:
    """返回所有已到期且 status=pending 的任务。"""
    root = workspace.resolve()
    paths = WorkspacePaths(root=root)
    queue_path = paths.schedule_queue_json
    tasks = _load_tasks(queue_path)
    now = datetime.now(timezone.utc)
    due: list[dict[str, Any]] = []
    for t in tasks:
        if t.get("status") != "pending":
            continue
        try:
            exec_dt = datetime.fromisoformat(t["exec_time_utc"])
            if exec_dt.tzinfo is None:
                exec_dt = exec_dt.replace(tzinfo=timezone.utc)
        except (KeyError, ValueError):
            continue
        if exec_dt <= now:
            due.append(t)
    return due


def mark_task_fired(workspace: Path, task_id: str) -> None:
    """标记任务为已触发。"""
    root = workspace.resolve()
    paths = WorkspacePaths(root=root)
    queue_path = paths.schedule_queue_json
    tasks = _load_tasks(queue_path)
    for t in tasks:
        if t.get("id") == task_id:
            t["status"] = "fired"
            t["fired_at"] = datetime.now(timezone.utc).isoformat()
            break
    _save_tasks(queue_path, tasks)
