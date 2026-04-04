"""
This module is used to log request and response details with timing.
Based on Option 2 in https://stackoverflow.com/a/73464007/31283770
"""

import json
import time
import uuid
from datetime import datetime
from typing import Any, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from fastapi import HTTPException
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
            state_request_id = getattr(request.state, "request_id", None)
            if state_request_id:
                request_id = str(state_request_id)
            else:
                request_id = request.headers.get("x-request-id") or str(uuid.uuid4())[:8]
                request.state.request_id = request_id

            # Use contextualize to add request_id to all logs in this request context
            with logger.contextualize(request_id=request_id):
                request_body = None

                # Determine log format based on configuration
                use_json_format = (
                    global_config_loaded_from_config_yaml.app.use_json_log_format
                )

                # Log request body for POST/PUT requests
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

                # Log request
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

                    # Extract response body
                    response_body = await self._extract_response_body(
                        response, request_id, request.method, request.url.path
                    )

                    # Log response
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

                    response.headers["x-request-id"] = request_id
                    return response
                except Exception as e:
                    duration = time.time() - start_time
                    # 401 鉴权失败（含 JWT 过期、未带 token）为预期情况，降级为 WARNING 减少 error 日志噪音
                    is_401 = (
                        isinstance(e, HTTPException)
                        and getattr(e, "status_code", None) == 401
                    )
                    if use_json_format:
                        error_log_data = {
                            "request_id": request_id,
                            "type": "error" if not is_401 else "warning",
                            "method": request.method,
                            "path": request.url.path,
                            "error": str(e),
                            "duration": round(duration, 3),
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                        }
                        if is_401:
                            logger.warning(
                                json.dumps(error_log_data, ensure_ascii=False)
                            )
                        else:
                            logger.error(json.dumps(error_log_data, ensure_ascii=False))
                    else:
                        if is_401:
                            logger.warning(
                                f"\n{'='*80}\n"
                                f"⚠️ 401 [{request_id}]\n"
                                f"{'='*80}\n"
                                f"Method:      {request.method}\n"
                                f"Path:        {request.url.path}\n"
                                f"Error:       {e}\n"
                                f"Duration:    {duration:.3f}s\n"
                            )
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

    async def _extract_response_body(
        self, response: Response, request_id: str, method: str, path: str
    ) -> Any:
        """
        Extract response body from various FastAPI response types.
        Supports JSONResponse, regular Response, and un-serialized responses.
        """
        response_type = type(response).__name__
        response_body = None
        extraction_error = None

        try:
            # Try method 1: For JSONResponse, try to access the underlying content
            # FastAPI's JSONResponse stores the content before serialization
            if isinstance(response, JSONResponse):
                try:
                    # JSONResponse may store content in different attributes
                    # Try _content first (internal attribute used by Starlette)
                    if hasattr(response, "_content") and response._content is not None:
                        try:
                            if isinstance(response._content, (dict, list)):
                                response_body = response._content
                                return response_body
                        except Exception:
                            pass

                    # Try content attribute (some versions of Starlette/FastAPI)
                    if hasattr(response, "content") and response.content is not None:
                        try:
                            # content might be a dict, list, or already serialized string
                            if isinstance(response.content, (dict, list)):
                                response_body = response.content
                                return response_body
                            elif isinstance(response.content, str):
                                try:
                                    response_body = json.loads(response.content)
                                except (json.JSONDecodeError, ValueError):
                                    response_body = response.content
                                return response_body
                        except Exception as e:
                            extraction_error = (
                                f"Failed to read JSONResponse.content: {e}"
                            )

                    # Fall through to try body attribute
                except Exception as e:
                    extraction_error = f"Failed to access JSONResponse attributes: {e}"

            # Try method 2: Direct body access (for responses that are already serialized)
            if hasattr(response, "body") and response.body is not None:
                try:
                    body_bytes = response.body
                    if body_bytes:
                        body_str = body_bytes.decode("utf-8")
                        try:
                            response_body = json.loads(body_str)
                        except (json.JSONDecodeError, ValueError):
                            response_body = body_str
                        return response_body
                except (AttributeError, UnicodeDecodeError, TypeError) as e:
                    if not extraction_error:
                        extraction_error = f"Failed to read response.body: {e}"

            # Try method 3: Read from body_iterator (for streaming responses)
            # Note: This consumes the iterator, so we need to recreate it
            if (
                hasattr(response, "body_iterator")
                and response.body_iterator is not None
            ):
                try:
                    # Check if it's already an async iterator
                    body_chunks = []
                    iterator = response.body_iterator
                    if hasattr(iterator, "__aiter__"):
                        async for chunk in iterator:
                            body_chunks.append(chunk)
                    elif hasattr(iterator, "__iter__"):
                        for chunk in iterator:
                            body_chunks.append(chunk)

                    if body_chunks:
                        body_bytes = b"".join(body_chunks)
                        body_str = body_bytes.decode("utf-8")
                        try:
                            response_body = json.loads(body_str)
                        except (json.JSONDecodeError, ValueError):
                            response_body = body_str

                        # Recreate body_iterator for the actual response
                        async def recreate_iterator():
                            yield body_bytes

                        response.body_iterator = recreate_iterator()
                        return response_body
                except (StopIteration, StopAsyncIteration):
                    # Iterator was already consumed, that's okay
                    pass
                except Exception as e:
                    if not extraction_error:
                        extraction_error = f"Failed to read from body_iterator: {e}"

        except Exception as e:
            extraction_error = f"Unexpected error: {e}"

        # Log warning if we couldn't extract the body
        if response_body is None and extraction_error:
            logger.warning(
                f"[{request_id}] Failed to extract response body: {extraction_error}, "
                f"method={method}, path={path}, "
                f"status={response.status_code}, response_type={response_type}, "
                f"has_body={hasattr(response, 'body')}, "
                f"has_body_iterator={hasattr(response, 'body_iterator')}, "
                f"is_jsonresponse={isinstance(response, JSONResponse)}"
            )

        return response_body

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
        logger.debug(json.dumps(log_data, ensure_ascii=False))

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
