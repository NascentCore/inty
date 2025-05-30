from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from jose.exceptions import JWTError
from pydantic import ValidationError

from app.core.config import settings
from app.api.v1.api import api_router
from app.middleware.error_handler import (
    validation_exception_handler,
    jwt_exception_handler,
    sqlalchemy_exception_handler,
    validation_error_handler
)

app = FastAPI(
    title=settings.app.name,
    openapi_url=f"{settings.app.api_v1_prefix}/openapi.json"
)

# Set all CORS enabled origins
if settings.app.backend_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.app.backend_cors_origins],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Register error handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(JWTError, jwt_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(ValidationError, validation_error_handler)

app.include_router(api_router, prefix=settings.app.api_v1_prefix)

@app.get("/")
async def root():
    """健康检查接口"""
    return {
        "code": 200,
        "message": "success",
        "data": {
            "app_name": settings.app.name,
            "version": "1.0.0"
        }
    } 