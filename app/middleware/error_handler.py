from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from jose.exceptions import JWTError
from pydantic import ValidationError


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "message": "Request validation failed",
            "data": {
                "detail": exc.errors()
            }
        }
    )


async def jwt_exception_handler(request: Request, exc: JWTError):
    """Handle JWT errors"""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "code": status.HTTP_401_UNAUTHORIZED,
            "message": "Invalid authentication credentials",
            "data": None
        }
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database errors"""
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"SQLAlchemy error: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "message": f"Database operation failed: {str(exc)}",
            "data": None
        }
    )


async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "message": "Data validation failed",
            "data": {
                "detail": exc.errors()
            }
        }
    ) 