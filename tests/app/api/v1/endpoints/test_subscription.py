import pytest
from inty import Inty
from loguru import logger


def test_get_subscription_usage():
    """Test getting subscription usage statistics"""
    # Create client with dummy API key to create guest user
    client = Inty(base_url="http://localhost:8000", api_key="dummy-api-key")

    # Create guest user
    guest_response = client.api.v1.auth.create_guest(
        device_id="test-device-usage-123",
        system_language="en",
        age_group="adult",
    )

    logger.debug(f"Guest registration response: {guest_response}")

    # Extract token and update client
    token = guest_response.data.token
    client = Inty(base_url="http://localhost:8000", api_key=token)

    # Call the subscription usage endpoint
    usage_response = client.api.v1.subscription.get_usage()

    logger.debug(f"Usage response: {usage_response}")

    # Verify response structure
    assert usage_response.data is not None, "Usage data should not be None"
