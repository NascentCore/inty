"""
This module is used to log request and response details with timing.
Based on Option 2 in https://stackoverflow.com/a/73464007/31283770
"""

import time
from typing import Callable
import uuid
import json
from fastapi import Request, Response
from fastapi.routing import APIRoute
from loguru import logger


class LoggerRoute(APIRoute):
    """
    Custom APIRoute class that logs request and response details with timing

    Based on
    https://fastapi.tiangolo.com/how-to/custom-request-and-route/#custom-apiroute-class-in-a-router
    With help from Cursor.
    """

    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            request_id = str(uuid.uuid4())
            request_body = None

            # Log request body for POST/PUT requests
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    body = await request.body()
                    if body:
                        # Try to decode as JSON for better readability
                        try:
                            import json

                            request_body = json.loads(body.decode())
                        except:
                            # If not JSON, log as string (truncated if too long)
                            request_body = (
                                body.decode()[:500] + "..."
                                if len(body) > 500
                                else body.decode()
                            )
                except Exception as e:
                    # Do nothing
                    # No body, so no request body to log
                    pass

            # Log request details
            logger.debug(
                f"[Request] {request_id} {request.method} {request.url.path} "
                f"Client: {request.client.host if request.client else 'unknown'} "
                f"User-Agent: {request.headers.get('user-agent', 'unknown')} "
                f"Query: {dict(request.query_params)} "
                f"Headers: {dict(request.headers)}"
                f"Request Body: {request_body}"
            )

            response_body = None
            try:
                start_time = time.time()
                response: Response = await original_route_handler(request)
                duration = time.time() - start_time

                try:
                    response_body = await response.body()
                    if response_body:
                        response_body = response_body.decode()[:500] + "..."
                        if len(response_body) > 500:
                            response_body = response_body[:500] + "..."
                except Exception as e:
                    # No body, so no response body to log
                    pass
                logger.debug(
                    f"[Response] {request_id} {request.method} {request.url.path} "
                    f"Headers: {dict(response.headers)} "
                    f"Status: {response.status_code} "
                    f"Response Body: {response_body} "
                    f"Duration: {duration:.3f}s "
                )
                return response
            except Exception as e:
                duration = time.time() - start_time
                logger.debug(
                    f"[Response] {request_id} {request.method} {request.url.path} "
                    f"Failed, error: {e} "
                    f"Duration: {duration:.3f}s "
                )
                raise

        return custom_route_handler
