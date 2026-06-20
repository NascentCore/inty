import pytest
from loguru import logger

from tests.app.api.test_client import TestClient


def test_get_subscription_usage(integration_client: TestClient):
    """Test getting subscription usage statistics"""
    response = integration_client.client.get(
        f"{integration_client.base_url}/api/v1/subscription/usage"
    )

    logger.debug(
        f"Usage response: status={response.status_code}, body={response.text}"
    )

    assert response.status_code == 200, response.text

    usage_response = response.json()

    assert (
        usage_response.get("data") is not None
    ), "Usage data should not be None"
