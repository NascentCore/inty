import time
from typing import Callable
from fastapi import Request, Response
from fastapi.routing import APIRoute
from loguru import logger


class TimedRoute(APIRoute):
    """
    Custom APIRoute class that logs request and response details with timing

    Based on
    https://fastapi.tiangolo.com/how-to/custom-request-and-route/#custom-apiroute-class-in-a-router
    With help from Cursor.
    """

    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            # Log request details
            logger.info(
                f"TimedRoute Request: {request.method} {request.url.path} "
                f"Client: {request.client.host if request.client else 'unknown'} "
                f"User-Agent: {request.headers.get('user-agent', 'unknown')} "
                f"Query: {dict(request.query_params)} "
                f"Headers: {dict(request.headers)}"
            )

            # Log request body for POST/PUT requests
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    body = await request.body()
                    if body:
                        # Try to decode as JSON for better readability
                        try:
                            import json

                            body_json = json.loads(body.decode())
                            logger.info(f"Request Body: {body_json}")
                        except:
                            # If not JSON, log as string (truncated if too long)
                            body_str = (
                                body.decode()[:500] + "..."
                                if len(body) > 500
                                else body.decode()
                            )
                            logger.info(f"Request Body: {body_str}")
                except Exception as e:
                    logger.warning(f"Could not read request body: {str(e)}")

            try:
                start_time = time.time()
                response: Response = await original_route_handler(request)
                duration = time.time() - start_time
                logger.info(
                    f"TimedRoute Response: {request.method} {request.url.path} "
                    f"Status: {response.status_code} "
                    f"Duration: {duration:.3f}s"
                )
                response.headers["X-Response-Time"] = f"{duration:.3f}s"
                return response
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"TimedRoute Error: {request.method} {request.url.path} "
                    f"Duration: {duration:.3f}s "
                    f"Error: {str(e)}"
                )
                raise

        return custom_route_handler
