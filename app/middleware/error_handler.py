from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from jose.exceptions import JWTError
from pydantic import ValidationError


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求验证错误"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "message": "请求参数验证失败",
            "data": {
                "detail": exc.errors()
            }
        }
    )


async def jwt_exception_handler(request: Request, exc: JWTError):
    """处理JWT错误"""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "code": status.HTTP_401_UNAUTHORIZED,
            "message": "无效的认证凭据",
            "data": None
        }
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """处理数据库错误"""
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"SQLAlchemy错误: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "message": f"数据库操作失败: {str(exc)}",
            "data": None
        }
    )


async def validation_error_handler(request: Request, exc: ValidationError):
    """处理Pydantic验证错误"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "message": "数据验证失败",
            "data": {
                "detail": exc.errors()
            }
        }
    ) 