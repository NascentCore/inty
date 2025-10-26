"""
This module is used to log request and response details with timing.
Based on Option 2 in https://stackoverflow.com/a/73464007/31283770
"""

import json
import time
import uuid
from datetime import datetime
from typing import Callable

from fastapi import Request, Response
from fastapi.routing import APIRoute
from loguru import logger

from app.core.config import global_config_loaded_from_config_yaml


class LoggerRoute(APIRoute):
    """
    Custom APIRoute class that logs request and response details with timing

    Based on
    https://fastapi.tiangolo.com/how-to/custom-request-and-route/#custom-apiroute-class-in-a-router
    With help from Cursor.
    """

    SENSITIVE_HEADERS = {
        "authorization",
        "cookie",
        "x-api-key",
        "x-auth-token",
    }

    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            request_id = str(uuid.uuid4())[:8]
# 使用 contextualize 将 request_id 添加到该请求上下文中的所有日志中
            with logger.contextualize(request_id=request_id):
                request_body = None
#根据调试确定模式日志格式
                use_json_format = not global_config_loaded_from_config_yaml.app.debug
# 记录 POST/PUT 请求的请求正文
                if request.method in ["POST", "PUT", "PATCH"]:
                    try:
                        body = await request.body()
                        if body:
                            try:
                                request_body = json.loads(body.decode())
                            except Exception:
                                request_body = body.decode()
                    except Exception:
                        pass
# 记录请求
                client = request.client.host if request.client else "unknown"
                if use_json_format:
                    self._log_request_json(
                        request_id=request_id,
                        method=request.method,
                        path=request.url.path,
                        client=client,
                        body=request_body,
                    )
                else:
                    filtered_headers = self._filter_headers(dict(request.headers))
                    self._log_request_readable(
                        request_id=request_id,
                        method=request.method,
                        path=request.url.path,
                        client=client,
                        user_agent=request.headers.get("user-agent", "unknown"),
                        query_params=dict(request.query_params),
                        headers=filtered_headers,
                        body=request_body,
                    )

                response_body = None
                try:
                    start_time = time.time()
                    response: Response = await original_route_handler(request)
                    duration = time.time() - start_time
# 提取响应体
                    try:
                        if hasattr(response, "body"):
                            body_bytes = response.body
                            if body_bytes:
                                body_str = body_bytes.decode("utf-8")
                                try:
                                    response_body = json.loads(body_str)
                                except Exception:
                                    response_body = body_str
                    except Exception:
                        pass
# 记录响应
                    if use_json_format:
                        self._log_response_json(
                            request_id=request_id,
                            method=request.method,
                            path=request.url.path,
                            status=response.status_code,
                            duration=duration,
                            body=response_body,
                        )
                    else:
                        self._log_response_readable(
                            request_id=request_id,
                            method=request.method,
                            path=request.url.path,
                            status=response.status_code,
                            duration=duration,
                            body=response_body,
                        )

                    return response
                except Exception as e:
                    duration = time.time() - start_time
                    if use_json_format:
                        error_log_data = {
                            "request_id": request_id,
                            "type": "error",
                            "method": request.method,
                            "path": request.url.path,
                            "error": str(e),
                            "duration": round(duration, 3),
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                        }
                        logger.error(json.dumps(error_log_data, ensure_ascii=False))
                    else:
                        self._log_error_readable(
                            request_id=request_id,
                            method=request.method,
                            path=request.url.path,
                            error=str(e),
                            duration=duration,
                        )
                    raise

        return custom_route_handler

    def _log_request_json(
        self, request_id: str, method: str, path: str, client: str, body
    ):
        """JSON format logging for request"""
        log_data = {
            "request_id": request_id,
            "type": "request",
            "method": method,
            "path": path,
            "client": client,
            "body": self._truncate_body(body, max_length=1000),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        logger.info(json.dumps(log_data, ensure_ascii=False))

    def _log_response_json(
        self,
        request_id: str,
        method: str,
        path: str,
        status: int,
        duration: float,
        body,
    ):
        """JSON format logging for response"""
        log_data = {
            "request_id": request_id,
            "type": "response",
            "method": method,
            "path": path,
            "status": status,
            "duration": round(duration, 3),
            "body": self._truncate_body(body, max_length=1000),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        if duration > 3.0:
            logger.warning(json.dumps(log_data, ensure_ascii=False))
        else:
            logger.info(json.dumps(log_data, ensure_ascii=False))

    def _log_request_readable(
        self,
        request_id: str,
        method: str,
        path: str,
        client: str,
        user_agent: str,
        query_params: dict,
        headers: dict,
        body,
    ):
        """Readable format logging for request (development)"""
        logger.debug(
            f"\n{'='*80}\n"
            f"📥 REQUEST [{request_id}]\n"
            f"{'='*80}\n"
            f"Method:      {method}\n"
            f"Path:        {path}\n"
            f"Client:      {client}\n"
            f"User-Agent:  {user_agent[:80]}\n"
            + (f"Query:       {query_params}\n" if query_params else "")
            + (
                f"Headers:     {json.dumps(headers, indent=2, ensure_ascii=False)}\n"
                if headers
                else ""
            )
            + (
                f"Body:        {json.dumps(body, indent=2, ensure_ascii=False) if isinstance(body, dict) else body}\n"
                if body
                else ""
            )
        )

    def _log_response_readable(
        self,
        request_id: str,
        method: str,
        path: str,
        status: int,
        duration: float,
        body,
    ):
        """Readable format logging for response (development)"""
        duration_emoji = "✅"
        if duration > 3.0:
            duration_emoji = "🚨"
        elif duration > 1.0:
            duration_emoji = "⚠️"

        logger.debug(
            f"\n{'='*80}\n"
            f"📤 RESPONSE [{request_id}] {duration_emoji}\n"
            f"{'='*80}\n"
            f"Method:      {method}\n"
            f"Path:        {path}\n"
            f"Status:      {status}\n"
            f"Duration:    {duration:.3f}s\n"
            + (
                f"Body:        {json.dumps(body, indent=2, ensure_ascii=False) if isinstance(body, dict) else body}\n"
                if body
                else ""
            )
        )

    def _log_error_readable(
        self, request_id: str, method: str, path: str, error: str, duration: float
    ):
        """Readable format logging for error (development)"""
        logger.error(
            f"\n{'='*80}\n"
            f"❌ RESPONSE ERROR [{request_id}]\n"
            f"{'='*80}\n"
            f"Method:      {method}\n"
            f"Path:        {path}\n"
            f"Error:       {error}\n"
            f"Duration:    {duration:.3f}s\n"
        )

    @classmethod
    def _filter_headers(cls, headers: dict) -> dict:
        """Filter out sensitive headers"""
        filtered = {}
        for key, value in headers.items():
            if key.lower() in cls.SENSITIVE_HEADERS:
                filtered[key] = "***REDACTED***"
            elif key.lower() in ["host", "content-type", "content-length", "accept"]:
                filtered[key] = value
        return filtered

    @staticmethod
    def _truncate_body(body, max_length: int = 1000):
        """Truncate body if it's too long"""
        if isinstance(body, dict):
            body_str = json.dumps(body, ensure_ascii=False)
            if len(body_str) > max_length:
                return {
                    "_truncated": True,
                    "original_size": len(body_str),
                    "keys": list(body.keys()),
                }
            return body
        elif isinstance(body, str):
            if len(body) > max_length:
                return body[:max_length] + "... (truncated)"
            return body
        return body
