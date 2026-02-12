from fastapi.routing import APIRouter
from pydantic import BaseModel
import pytest
import json
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient

from app.api.utils.logger_route import (
    LoggerRoute,
    build_sentry_transaction_name,
    resolve_route_path_from_scope,
)
from app.schemas.response import APIResponse


# Create a test app with an endpoint that uses read_body
app = FastAPI()

router = APIRouter(route_class=LoggerRoute)


class Item(BaseModel):
    id: str
    title: str
    description: str | None = None


@router.post("/test-read-body", response_model=Item)
async def create_item(item: Item):
    return item


@router.post("/test-api-response", response_model=APIResponse[Item])
async def create_item_with_api_response(item: Item):
    return APIResponse.success(data=item)


@router.get("/test-dict-response")
async def get_dict_response():
    return {"status": "success", "message": "test"}


app.include_router(router)

client = TestClient(app)


class TestLoggerRoute:
    """Test cases for logger_route module using TestClient"""

    def test_build_sentry_transaction_name_uses_uppercase_method(self):
        transaction_name = build_sentry_transaction_name(
            method="get",
            route_path="/api/v1/users/{user_id}",
        )
        assert transaction_name == "GET /api/v1/users/{user_id}"

    def test_resolve_route_path_from_scope_prefers_route_path(self):
        class MockRoute:
            path = "/api/v1/users/{user_id}"

        route_path = resolve_route_path_from_scope(
            scope={"route": MockRoute()},
            fallback_path="/api/v1/users/123",
        )
        assert route_path == "/api/v1/users/{user_id}"

    def test_resolve_route_path_from_scope_fallback_to_path_format(self):
        class MockRoute:
            path = None
            path_format = "/api/v1/evaluation/sessions/{session_id}/monitor"

        route_path = resolve_route_path_from_scope(
            scope={"route": MockRoute()},
            fallback_path="/api/v1/evaluation/sessions/abc/monitor",
        )
        assert route_path == "/api/v1/evaluation/sessions/{session_id}/monitor"

    def test_resolve_route_path_from_scope_returns_fallback_when_missing_route(self):
        route_path = resolve_route_path_from_scope(
            scope={},
            fallback_path="/api/v1/users/123",
        )
        assert route_path == "/api/v1/users/123"

    def test_read_body_request_json_happy_case(self):
        """Test read_body function with JSON request body using TestClient"""
        # Arrange
        item = Item(id="1", title="test", description="test")

        # Act
        response = client.post("/test-read-body", json=item.model_dump())

        # Assert
        assert response.status_code == 200
        assert response.json() == item.model_dump()

    def test_response_body_logging_with_api_response(self):
        """Test that response body is logged correctly for APIResponse"""
        # Arrange
        item = Item(id="2", title="test2", description="test2")

        # Act
        response = client.post("/test-api-response", json=item.model_dump())

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["code"] == 200
        assert response_data["data"]["id"] == "2"

    def test_response_body_logging_with_dict_response(self):
        """Test that response body is logged correctly for dict response"""
        # Act
        response = client.get("/test-dict-response")

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "success"
        assert response_data["message"] == "test"
