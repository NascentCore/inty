from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from jose.exceptions import JWTError
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

import logging

logger = logging.getLogger(__name__)


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

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "message": "Request validation failed",
            "data": {"detail": exc.errors()},
        },
    )


async def jwt_exception_handler(request: Request, exc: JWTError):
    """Handle JWT errors"""
    logger.error(f"=== JWT认证错误 (401错误) ===")
    logger.error(f"请求方法: {request.method}")
    logger.error(f"请求URL: {request.url}")
    logger.error(f"JWT错误: {str(exc)}")
    logger.error(f"JWT错误类型: {type(exc).__name__}")
    logger.error(f"=== JWT错误详情结束 ===")

    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "code": status.HTTP_401_UNAUTHORIZED,
            "message": "Invalid authentication credentials",
            "data": None,
        },
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database errors"""
    logger.error(f"=== 数据库错误 (500错误) ===")
    logger.error(f"请求方法: {request.method}")
    logger.error(f"请求URL: {request.url}")
    logger.error(f"SQLAlchemy错误: {str(exc)}")
    logger.error(f"SQLAlchemy错误类型: {type(exc).__name__}")
    logger.error(f"=== 数据库错误详情结束 ===")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "message": f"Database operation failed: {str(exc)}",
            "data": None,
        },
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

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "message": "Data validation failed",
            "data": {"detail": exc.errors()},
        },
    )
