import asyncio
from typing import Dict

from fastapi import FastAPI, HTTPException

from .models import (
    NotifyRequest,
    StartTaskRequest,
    StartTaskResponse,
    TaskStatusResponse,
)
from .firebase_client import send_message_to_token
from .tasks import create_task, get_task, run_task_and_notify

app = FastAPI(title="Android Firebase Server Tasks Demo")


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/start_task", response_model=StartTaskResponse)
async def start_task(req: StartTaskRequest) -> StartTaskResponse:
    task = create_task(
        device_token=req.device_token,
        task_name=req.task_name,
        duration_seconds=req.duration_seconds,
    )
    asyncio.create_task(run_task_and_notify(task.task_id))
    return StartTaskResponse(task_id=task.task_id, status=task.status)


@app.get("/task/{task_id}", response_model=TaskStatusResponse)
async def task_status(task_id: str) -> TaskStatusResponse:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return TaskStatusResponse(
        task_id=task.task_id,
        status=task.status,
        task_name=task.task_name,
        duration_seconds=task.duration_seconds,
    )


@app.post("/notify")
async def notify(req: NotifyRequest) -> Dict[str, str]:
    message_id = send_message_to_token(
        device_token=req.device_token,
        title=req.title,
        body=req.body,
        data={k: str(v) for k, v in (req.data or {}).items()},
    )
    return {"message_id": message_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "experimental.android_firebase_server_tasks.fastapi_server:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
    )
