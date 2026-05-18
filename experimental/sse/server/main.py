import asyncio
import json
import uuid
from typing import AsyncGenerator, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

KEEPALIVE_SECONDS: float = 15.0
DEFAULT_EVENT_NAME: str = "message"


class PublishRequest(BaseModel):
    message: str
    event: Optional[str] = None


class StartTaskRequest(BaseModel):
    client_id: str
    seconds: float = 3.0


class MessageBroker:
    def __init__(self) -> None:
        self._subscribers_by_client: dict[str, set[asyncio.Queue[str]]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, client_id: str) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        async with self._lock:
            if client_id not in self._subscribers_by_client:
                self._subscribers_by_client[client_id] = set()
            self._subscribers_by_client[client_id].add(queue)
        return queue

    async def unsubscribe(
        self, client_id: str, queue: asyncio.Queue[str]
    ) -> None:
        async with self._lock:
            queues = self._subscribers_by_client.get(client_id)
            if queues is not None:
                queues.discard(queue)
                if not queues:
                    self._subscribers_by_client.pop(client_id, None)

    async def publish_to_client(
        self, client_id: str, data: str, event: Optional[str] = None
    ) -> None:
        event_name = event or DEFAULT_EVENT_NAME
        payload = f"event: {event_name}\ndata: {data}\n\n"
        async with self._lock:
            targets = list(self._subscribers_by_client.get(client_id, set()))
        for q in targets:
            await q.put(payload)

    async def publish_broadcast(
        self, data: str, event: Optional[str] = None
    ) -> None:
        event_name = event or DEFAULT_EVENT_NAME
        payload = f"event: {event_name}\ndata: {data}\n\n"
        async with self._lock:
            targets: list[asyncio.Queue[str]] = []
            for queues in self._subscribers_by_client.values():
                targets.extend(list(queues))
        for q in targets:
            await q.put(payload)


broker = MessageBroker()
app = FastAPI(title="Minimal SSE Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/stream")
async def stream(request: Request) -> StreamingResponse:
    client_id = request.query_params.get("client_id")
    if not client_id:
        return StreamingResponse(
            (line async for line in _error_stream("missing client_id")),
            media_type="text/event-stream",
        )

    subscriber_queue = await broker.subscribe(client_id)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Optional greeting so clients see something immediately
            yield "event: open\ndata: connected\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(
                        subscriber_queue.get(), timeout=KEEPALIVE_SECONDS
                    )
                    yield payload
                except asyncio.TimeoutError:
                    # Keep-alive ping so intermediaries don't close idle connection
                    yield "event: ping\ndata: keepalive\n\n"
        finally:
            await broker.unsubscribe(client_id, subscriber_queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/publish")
async def publish(req: PublishRequest) -> JSONResponse:
    # Broadcast utility kept for completeness
    await broker.publish_broadcast(req.message, req.event)
    return JSONResponse({"status": "ok"})


async def _long_running_task(
    client_id: str, task_id: str, seconds: float
) -> None:
    await asyncio.sleep(max(0.0, seconds))
    payload = json.dumps({"task_id": task_id, "status": "completed"})
    await broker.publish_to_client(client_id, payload, event="task_complete")


@app.post("/start_task")
async def start_task(req: StartTaskRequest) -> JSONResponse:
    task_id = str(uuid.uuid4())
    asyncio.create_task(_long_running_task(req.client_id, task_id, req.seconds))
    return JSONResponse(
        {"task_id": task_id, "status": "started", "eta_seconds": req.seconds}
    )


async def _error_stream(message: str) -> AsyncGenerator[str, None]:
    yield f"event: error\ndata: {message}\n\n"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8009, reload=False)
