"""Tests that demo APIResponse serialization to dict and JSON string.

APIResponse is a Pydantic BaseModel; serialization uses model_dump() and model_dump_json().
"""

import json

from pydantic import BaseModel

from app.schemas.response import APIResponse


def test_success_response_default_no_data():
    """Success response with no data: model_dump and model_dump_json match expected shape."""
    resp = APIResponse.success()
    assert isinstance(resp, APIResponse)
    assert resp.code == 200
    assert resp.message == "success"
    assert resp.data is None
    assert resp.model_dump() == {
        "code": 200,
        "message": "success",
        "data": None,
    }
    assert json.loads(resp.model_dump_json()) == {
        "code": 200,
        "message": "success",
        "data": None,
    }


def test_success_response_with_data():
    """Success response with dict data: serialized dict and JSON contain payload."""
    payload = {"key": "value"}
    resp = APIResponse.success(data=payload)
    assert isinstance(resp, APIResponse)
    assert resp.code == 200
    assert resp.message == "success"
    assert resp.data == payload
    assert resp.model_dump() == {
        "code": 200,
        "message": "success",
        "data": payload,
    }
    assert json.loads(resp.model_dump_json()) == {
        "code": 200,
        "message": "success",
        "data": payload,
    }


def test_error_response_default_code():
    """Error response with default code 400: model_dump and JSON show code, message, null data."""
    resp = APIResponse.error(message="Bad request")
    assert isinstance(resp, APIResponse)
    assert resp.code == 400
    assert resp.message == "Bad request"
    assert resp.data is None
    assert resp.model_dump() == {
        "code": 400,
        "message": "Bad request",
        "data": None,
    }
    assert json.loads(resp.model_dump_json()) == {
        "code": 400,
        "message": "Bad request",
        "data": None,
    }


def test_error_response_custom_code_and_data():
    """Error response with custom code and data: serialized output includes data payload."""
    payload = {"error_code": "NOT_FOUND"}
    resp = APIResponse.error(message="Not found", code=404, data=payload)
    assert isinstance(resp, APIResponse)
    assert resp.code == 404
    assert resp.message == "Not found"
    assert resp.data == payload
    assert resp.model_dump() == {
        "code": 404,
        "message": "Not found",
        "data": payload,
    }
    assert json.loads(resp.model_dump_json()) == {
        "code": 404,
        "message": "Not found",
        "data": payload,
    }


def test_success_response_with_nested_pydantic_model():
    """Success response with Pydantic model as data: nested model is serialized recursively."""
    class Item(BaseModel):
        id: str
        title: str

    item = Item(id="1", title="Demo")
    resp = APIResponse.success(data=item)
    expected_data = {"id": "1", "title": "Demo"}
    assert isinstance(resp, APIResponse)
    assert resp.code == 200
    assert resp.message == "success"
    assert resp.model_dump() == {
        "code": 200,
        "message": "success",
        "data": expected_data,
    }
    assert json.loads(resp.model_dump_json()) == {
        "code": 200,
        "message": "success",
        "data": expected_data,
    }
