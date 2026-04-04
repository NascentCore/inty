import time
import uuid

from fastapi import Request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "path", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        state_request_id = getattr(request.state, "request_id", None)
        request_id = (
            str(state_request_id)
            if state_request_id
            else request.headers.get("x-request-id") or uuid.uuid4().hex[:8]
        )
        request.state.request_id = request_id

        start_time = time.perf_counter()
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            duration = time.perf_counter() - start_time
            request_path = _resolve_request_path(request)
            http_requests_total.labels(
                method=request.method,
                path=request_path,
                status_code="500",
            ).inc()
            http_request_duration_seconds.labels(
                method=request.method,
                path=request_path,
            ).observe(duration)
            raise

        duration = time.perf_counter() - start_time
        request_path = _resolve_request_path(request)
        http_requests_total.labels(
            method=request.method,
            path=request_path,
            status_code=str(status_code),
        ).inc()
        http_request_duration_seconds.labels(
            method=request.method,
            path=request_path,
        ).observe(duration)
        response.headers["x-request-id"] = request_id
        return response


def metrics_response() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


def _resolve_request_path(request: Request) -> str:
    route = request.scope.get("route")
    route_path = getattr(route, "path", None)
    if route_path:
        return route_path
    return request.url.path
