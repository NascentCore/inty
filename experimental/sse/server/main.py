import asyncio
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


class MessageBroker:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[str]] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        async with self._lock:
            self._subscribers.add(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        async with self._lock:
            self._subscribers.discard(queue)

    async def publish(self, data: str, event: Optional[str] = None) -> None:
        # Pre-format as SSE payload to simplify generator
        event_name = event or DEFAULT_EVENT_NAME
        payload = f"event: {event_name}\ndata: {data}\n\n"
        async with self._lock:
            targets = list(self._subscribers)
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
    subscriber_queue = await broker.subscribe()

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
            await broker.unsubscribe(subscriber_queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/publish")
async def publish(req: PublishRequest) -> JSONResponse:
    await broker.publish(req.message, req.event)
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8009, reload=False)
