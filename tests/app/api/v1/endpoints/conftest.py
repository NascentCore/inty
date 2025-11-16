import os

import pytest

from tests.app.api.test_client import TestClient

API_BASE_URL = os.getenv("INTY_API_BASE_URL", "http://localhost:8000")


@pytest.fixture
def integration_client():
    client = TestClient(API_BASE_URL)
    client.create_user()
    try:
        yield client
    finally:
        client.delete_user()
        client.close()
