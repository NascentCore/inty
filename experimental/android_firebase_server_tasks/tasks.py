import asyncio
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Dict

from .firebase_client import send_message_to_token

from loguru import logger


@dataclass
class TaskInfo:
    task_id: str
    task_name: str
    duration_seconds: int
    device_token: str
    status: str
    created_at_epoch: float


_TASKS: Dict[str, TaskInfo] = {}
_TASKS_LOCK = threading.Lock()


def create_task(
    *, device_token: str, task_name: str, duration_seconds: int
) -> TaskInfo:
    task_id = str(uuid.uuid4())
    task = TaskInfo(
        task_id=task_id,
        task_name=task_name,
        duration_seconds=duration_seconds,
        device_token=device_token,
        status="queued",
        created_at_epoch=time.time(),
    )
    with _TASKS_LOCK:
        _TASKS[task_id] = task
    return task


def get_task(task_id: str) -> TaskInfo | None:
    with _TASKS_LOCK:
        return _TASKS.get(task_id)


async def run_task_and_notify(task_id: str) -> None:
    task = get_task(task_id)
    if task is None:
        return

    task.status = "running"
    await asyncio.sleep(task.duration_seconds)
    task.status = "completed"

    title = "任务完成"
    body = f"{task.task_name} 已完成"
    data = {
        "event": "task_completed",
        "task_id": task.task_id,
        "task_name": task.task_name,
    }

    try:
        send_message_to_token(
            device_token=task.device_token, title=title, body=body, data=data
        )
    except Exception as err:
        logger.debug("Failed to send completion notification: %s", err)
        task.status = "completed_notification_failed"
