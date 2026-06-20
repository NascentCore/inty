import uuid

import pytest
import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 15


@pytest.mark.noci
def test_request_id_header_is_propagated_for_success_and_error():
    provided_request_id = f"req-{uuid.uuid4().hex[:10]}"
    headers = {"x-request-id": provided_request_id}

    success_response = requests.get(
        f"{BASE_URL}/",
        headers=headers,
        timeout=TIMEOUT,
    )
    assert success_response.status_code == 200
    assert success_response.headers.get("x-request-id") == provided_request_id

    error_response = requests.get(
        f"{BASE_URL}/api/v1/users/me",
        headers=headers,
        timeout=TIMEOUT,
    )
    assert error_response.status_code == 401
    assert error_response.headers.get("x-request-id") == provided_request_id
    body = error_response.json()
    assert body.get("request_id") == provided_request_id


@pytest.mark.noci
def test_metrics_endpoint_exposes_http_metrics():
    trigger_response = requests.get(f"{BASE_URL}/", timeout=TIMEOUT)
    assert trigger_response.status_code == 200

    metrics_response = requests.get(f"{BASE_URL}/metrics", timeout=TIMEOUT)
    assert metrics_response.status_code == 200
    metrics_text = metrics_response.text
    assert "http_requests_total" in metrics_text
    assert "http_request_duration_seconds" in metrics_text


@pytest.mark.noci
def test_metrics_path_label_is_bounded_for_unmatched_routes():
    random_path = f"/no-such-path-{uuid.uuid4().hex}"
    not_found_response = requests.get(
        f"{BASE_URL}{random_path}", timeout=TIMEOUT
    )
    assert not_found_response.status_code == 404

    metrics_response = requests.get(f"{BASE_URL}/metrics", timeout=TIMEOUT)
    assert metrics_response.status_code == 200
    metrics_text = metrics_response.text
    assert random_path not in metrics_text
    assert 'path="__unmatched__"' in metrics_text
