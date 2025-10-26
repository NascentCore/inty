from fastapi.routing import APIRouter
from pydantic import BaseModel
import pytest
import json
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient

from app.api.utils.logger_route import LoggerRoute
# 创建一个测试应用程序，其端点使用read_body
app = FastAPI()

router = APIRouter(route_class=LoggerRoute)


class Item(BaseModel):
    id: str
    title: str
    description: str | None = None


@router.post("/test-read-body", response_model=Item)
async def create_item(item: Item):
    return item


app.include_router(router)

client = TestClient(app)


class TestLoggerRoute:
    """Test cases for logger_route module using TestClient"""

    def test_read_body_request_json_happy_case(self):
        """Test read_body function with JSON request body using TestClient"""
＃ 安排
        item = Item(id="1", title="test", description="test")
＃ 行为
        response = client.post("/test-read-body", json=item.model_dump())
#断言
        assert response.status_code == 200
        assert response.json() == item.model_dump()
