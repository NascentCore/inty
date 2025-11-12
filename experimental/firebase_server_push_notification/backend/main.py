"""FastAPI 示例：接受处理请求，模拟长任务并通过 Firebase 发送完成通知。

运行前准备：
- 在环境变量 `FIREBASE_SERVICE_ACCOUNT_FILE` 或 `GOOGLE_APPLICATION_CREDENTIALS` 中提供 Firebase 服务账号 JSON 路径。
- 通过 `pip install -r requirements.txt` 安装依赖后运行 `uvicorn backend.main:app --reload`。
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from typing import Any, Dict, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
except ModuleNotFoundError:  # pragma: no cover - 仅在未安装 firebase-admin 时触发
    firebase_admin = None
    messaging = None
    credentials = None


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class JobStatus(str):
    PENDING = "pending"
    FINISHED = "finished"


class JobResult(BaseModel):
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None


class ProcessRequest(BaseModel):
    device_token: str
    payload: Optional[Dict[str, Any]] = None


class ResultStore:
    """简单的内存结果存储，示例用途。"""

    def __init__(self) -> None:
        self._results: Dict[str, JobResult] = {}
        self._lock = asyncio.Lock()

    async def create_job(self, job_id: str) -> None:
        async with self._lock:
            self._results[job_id] = JobResult(job_id=job_id, status=JobStatus.PENDING)

    async def set_result(self, job_id: str, data: Dict[str, Any]) -> None:
        async with self._lock:
            if job_id not in self._results:
                self._results[job_id] = JobResult(job_id=job_id, status=JobStatus.FINISHED, result=data)
                return
            self._results[job_id].status = JobStatus.FINISHED
            self._results[job_id].result = data

    async def get_job(self, job_id: str) -> JobResult:
        async with self._lock:
            job = self._results.get(job_id)
            if not job:
                raise KeyError(job_id)
            return job


class FirebaseNotifier:
    def __init__(self) -> None:
        self._app: Optional[firebase_admin.App] = None
        self._initialize()

    def _initialize(self) -> None:
        if firebase_admin is None:
            logger.warning("未安装 firebase-admin，推送功能将不可用")
            return

        if firebase_admin._apps:  # type: ignore[attr-defined]
            self._app = firebase_admin.get_app()
            return

        cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_FILE") or os.getenv(
            "GOOGLE_APPLICATION_CREDENTIALS"
        )
        if not cred_path:
            logger.warning("未配置 FIREBASE_SERVICE_ACCOUNT_FILE，推送不会生效")
            return

        # 参考 Firebase Admin 初始化文档: https://firebase.google.com/docs/admin/setup?hl=zh-cn
        cred = credentials.Certificate(cred_path)
        self._app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin 已初始化")

    async def notify_job_finished(self, device_token: str, job_id: str) -> None:
        if messaging is None or self._app is None:
            logger.warning("Firebase 未初始化，跳过推送 job_id=%s", job_id)
            return

        # 构造消息的字段说明见官方文档: https://firebase.google.com/docs/cloud-messaging/send-message?hl=zh-cn#admin
        message = messaging.Message(
            token=device_token,
            data={"job_id": job_id, "result_ready": "true"},
            notification=messaging.Notification(
                title="任务处理完成",
                body=f"结果 ID: {job_id}",
            ),
        )

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, messaging.send, message)
        logger.info("已发送推送 job_id=%s", job_id)


result_store = ResultStore()
notifier = FirebaseNotifier()
app = FastAPI(title="Firebase Server Push Demo")


async def process_job(job_id: str, device_token: str, payload: Optional[Dict[str, Any]]) -> None:
    """模拟耗时任务：等待 5 秒并生成结果。"""

    logger.info("开始处理 job_id=%s", job_id)
    await asyncio.sleep(5)  # 示例等待 5 秒，实际可以改成 300 秒

    result_data = {
        "processed_at": asyncio.get_running_loop().time(),
        "payload": payload or {},
        "message": "示例任务已完成",
    }
    await result_store.set_result(job_id, result_data)
    await notifier.notify_job_finished(device_token=device_token, job_id=job_id)
    logger.info("完成处理 job_id=%s", job_id)


@app.post("/process", response_model=JobResult)
async def submit_process(request: ProcessRequest, background_tasks: BackgroundTasks) -> JobResult:
    job_id = uuid.uuid4().hex
    await result_store.create_job(job_id)
    background_tasks.add_task(process_job, job_id, request.device_token, request.payload)
    logger.info("收到新任务 job_id=%s", job_id)
    return JobResult(job_id=job_id, status=JobStatus.PENDING)


@app.get("/results/{job_id}", response_model=JobResult)
async def fetch_result(job_id: str) -> JobResult:
    try:
        job = await result_store.get_job(job_id)
        return job
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"job_id {job_id} 不存在") from exc


@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "ok"}
