import logging
import traceback

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from jose.exceptions import JWTError
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

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


async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions (500 errors)"""
    logger.error(f"=== 通用服务器错误 (500错误) ===")
    logger.error(f"请求方法: {request.method}")
    logger.error(f"请求URL: {request.url}")
    logger.error(f"请求路径: {request.url.path}")
    logger.error(f"请求头: {dict(request.headers)}")
    
    # 记录异常详情
    logger.error(f"异常类型: {type(exc).__name__}")
    logger.error(f"异常消息: {str(exc)}")
    logger.error(f"异常堆栈跟踪:")
    logger.error(traceback.format_exc())
    
    # 记录请求体信息（如果可能）
    try:
        body = await request.body()
        logger.error(f"请求体大小: {len(body)} bytes")
        if len(body) < 1000:  # 只记录小文件的内容
            logger.error(f"请求体内容: {body.decode('utf-8', errors='ignore')}")
    except Exception as e:
        logger.error(f"无法读取请求体: {str(e)}")
    
    logger.error(f"=== 通用服务器错误详情结束 ===")

    # 根据环境决定是否返回详细错误信息
    from app.core.config import global_config_loaded_from_config_yaml
    
    if global_config_loaded_from_config_yaml.app.debug:
        # 调试模式：返回详细错误信息
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Internal server error: {str(exc)}",
                "data": {
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "traceback": traceback.format_exc(),
                    "request_info": {
                        "method": request.method,
                        "url": str(request.url),
                        "path": request.url.path,
                    }
                },
            },
        )
    else:
        # 生产模式：返回通用错误信息
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": None,
            },
        )
