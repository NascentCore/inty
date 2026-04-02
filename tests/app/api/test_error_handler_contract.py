from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.middleware.error_handler import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError


def test_http_exception_uses_unified_error_envelope():
    app = FastAPI()
    app.add_exception_handler(HTTPException, http_exception_handler)

    @app.get("/boom")
    async def boom():
        raise HTTPException(status_code=404, detail="missing resource")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "NOT_FOUND"
    assert body["message"] == "missing resource"
    assert body["details"] == {"detail": "missing resource"}
    assert isinstance(body["request_id"], str)
    assert body["request_id"]
    assert response.headers["x-request-id"] == body["request_id"]


def test_validation_exception_uses_unified_error_envelope():
    app = FastAPI()
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    @app.get("/needs-int/{value}")
    async def needs_int(value: int):
        return {"value": value}

    client = TestClient(app)
    response = client.get("/needs-int/not-an-int")

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "UNPROCESSABLE_ENTITY"
    assert body["message"] == "Request validation failed"
    assert isinstance(body["details"], list)
    assert isinstance(body["request_id"], str)
    assert body["request_id"]
    assert response.headers["x-request-id"] == body["request_id"]


def test_unhandled_exception_uses_unified_error_envelope():
    app = FastAPI()
    app.add_exception_handler(Exception, unhandled_exception_handler)

    @app.get("/explode")
    async def explode():
        raise RuntimeError("unexpected")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/explode")

    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "INTERNAL_SERVER_ERROR"
    assert body["message"] == "Internal server error"
    assert body["details"] == {"error_type": "RuntimeError"}
    assert isinstance(body["request_id"], str)
    assert body["request_id"]
    assert response.headers["x-request-id"] == body["request_id"]
