import uuid
from typing import Any, Optional

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from jose.exceptions import JWTError, ExpiredSignatureError
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from loguru import logger

from app.schemas.response import APIErrorResponse


HTTP_STATUS_ERROR_CODE_MAP = {
    status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
    status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
    status.HTTP_409_CONFLICT: "CONFLICT",
    status.HTTP_422_UNPROCESSABLE_ENTITY: "UNPROCESSABLE_ENTITY",
    status.HTTP_429_TOO_MANY_REQUESTS: "TOO_MANY_REQUESTS",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "INTERNAL_SERVER_ERROR",
    status.HTTP_503_SERVICE_UNAVAILABLE: "SERVICE_UNAVAILABLE",
}


def map_http_status_to_error_code(status_code: int) -> str:
    return HTTP_STATUS_ERROR_CODE_MAP.get(status_code, "HTTP_ERROR")


def _get_request_id(request: Request) -> str:
    state_request_id = getattr(request.state, "request_id", None)
    if state_request_id:
        return str(state_request_id)

    header_request_id = request.headers.get("x-request-id")
    if header_request_id:
        request.state.request_id = header_request_id
        return header_request_id

    generated_request_id = uuid.uuid4().hex[:8]
    request.state.request_id = generated_request_id
    return generated_request_id


def _build_error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: Optional[Any] = None,
) -> JSONResponse:
    request_id = _get_request_id(request)
    response_payload = APIErrorResponse(
        code=code,
        message=message,
        details=details,
        request_id=request_id,
    )
    response = JSONResponse(
        status_code=status_code,
        content=response_payload.model_dump(),
    )
    response.headers["x-request-id"] = request_id
    return response


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    logger.error(f"=== 请求验证失败 (422错误) ===")
    logger.error(f"请求方法: {request.method}")
    logger.error(f"请求URL: {request.url}")
    logger.error(f"请求路径: {request.url.path}")
    logger.error(f"请求头: {dict(request.headers)}")

    # 记录请求体信息（如果可能）
    try:
        body = await request.body()
        logger.error(f"请求体大小: {len(body)} bytes")
        if len(body) < 1000:  # 只记录小文件的内容
            logger.error(f"请求体内容: {body.decode('utf-8', errors='ignore')}")
    except Exception as e:
        logger.error(f"无法读取请求体: {str(e)}")

    # 记录详细的验证错误
    logger.error(f"验证错误数量: {len(exc.errors())}")
    for i, error in enumerate(exc.errors()):
        logger.error(f"错误 {i+1}:")
        logger.error(f"  类型: {error['type']}")
        logger.error(f"  位置: {error['loc']}")
        logger.error(f"  消息: {error['msg']}")
        logger.error(f"  输入: {error.get('input', 'N/A')}")

    logger.error(f"=== 验证错误详情结束 ===")

    return _build_error_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code=map_http_status_to_error_code(status.HTTP_422_UNPROCESSABLE_ENTITY),
        message="Request validation failed",
        details=exc.errors(),
    )


async def jwt_exception_handler(request: Request, exc: JWTError):
    """Handle JWT errors. Expired tokens are logged as WARNING to reduce error log noise."""
    if isinstance(exc, ExpiredSignatureError):
        logger.warning(
            f"JWT已过期 (401): {request.method} {request.url.path} - {type(exc).__name__}: {exc}"
        )
    else:
        logger.error(f"=== JWT认证错误 (401错误) ===")
        logger.error(f"请求方法: {request.method}")
        logger.error(f"请求URL: {request.url}")
        logger.error(f"JWT错误: {str(exc)}")
        logger.error(f"JWT错误类型: {type(exc).__name__}")
        logger.error(f"=== JWT错误详情结束 ===")

    return _build_error_response(
        request=request,
        status_code=status.HTTP_401_UNAUTHORIZED,
        code=map_http_status_to_error_code(status.HTTP_401_UNAUTHORIZED),
        message="Invalid authentication credentials",
        details=None,
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database errors"""
    logger.error(f"=== 数据库错误 (500错误) ===")
    logger.error(f"请求方法: {request.method}")
    logger.error(f"请求URL: {request.url}")
    logger.error(f"SQLAlchemy错误: {str(exc)}")
    logger.error(f"SQLAlchemy错误类型: {type(exc).__name__}")
    logger.error(f"=== 数据库错误详情结束 ===")

    return _build_error_response(
        request=request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="DATABASE_ERROR",
        message="Database operation failed",
        details={"error": str(exc)},
    )


async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors"""
    logger.error(f"=== Pydantic验证错误 (422错误) ===")
    logger.error(f"请求方法: {request.method}")
    logger.error(f"请求URL: {request.url}")
    logger.error(f"Pydantic错误: {str(exc)}")
    logger.error(f"Pydantic错误类型: {type(exc).__name__}")

    # 记录详细的验证错误
    if hasattr(exc, "errors"):
        logger.error(f"验证错误数量: {len(exc.errors())}")
        for i, error in enumerate(exc.errors()):
            logger.error(f"错误 {i+1}:")
            logger.error(f"  类型: {error['type']}")
            logger.error(f"  位置: {error['loc']}")
            logger.error(f"  消息: {error['msg']}")
            logger.error(f"  输入: {error.get('input', 'N/A')}")

    logger.error(f"=== Pydantic验证错误详情结束 ===")

    return _build_error_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code=map_http_status_to_error_code(status.HTTP_422_UNPROCESSABLE_ENTITY),
        message="Data validation failed",
        details=exc.errors(),
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException | HTTPException
):
    status_code = exc.status_code
    details = {"detail": exc.detail}

    if isinstance(exc.detail, str):
        message = exc.detail
    else:
        message = "Request failed"

    return _build_error_response(
        request=request,
        status_code=status_code,
        code=map_http_status_to_error_code(status_code),
        message=message,
        details=details,
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled server error: {type(exc).__name__}: {exc}")
    return _build_error_response(
        request=request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code=map_http_status_to_error_code(status.HTTP_500_INTERNAL_SERVER_ERROR),
        message="Internal server error",
        details={"error_type": type(exc).__name__},
    )
