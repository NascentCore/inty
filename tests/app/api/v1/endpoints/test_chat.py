"""
Integration tests for chat endpoints using Python SDK.
"""

import os
import uuid

import pytest
from inty import Inty
from loguru import logger


@pytest.fixture
def inty_client():
    """Create Inty client for testing."""
    # Use local development server
    client = Inty(
        base_url="http://localhost:8000",
        api_key="test-api-key",
    )
    response = client.api.v1.auth.create_guest(
        age_group="adult",
        device_id=f"test-device-{uuid.uuid4().hex[:8]}",
        system_language="en",
    )
    logger.info(f"Guest registration response: {response}")

    # Create authenticated client
    auth_client = Inty(
        base_url="http://localhost:8000",
        api_key=response.data.token,
    )

    yield auth_client

    # Cleanup: Delete guest user
    logger.info(f"Cleaning up guest user: {response.data.guest_id}")
    auth_client.api.v1.users.delete_account()
    logger.info("Guest user deleted successfully")


@pytest.fixture(scope="function")
def agent_ids_to_cleanup(inty_client):
    agent_ids = []
    yield agent_ids
    for agent_id in agent_ids:
        logger.info(f"Deleting agent: {agent_id}")
        inty_client.api.v1.ai.agents.delete(agent_id=agent_id)
        logger.info(f"Deleted agent: {agent_id}")


def test_agent_chat_completions_with_sdk(inty_client, agent_ids_to_cleanup):
    """Test chat completions using the Python SDK."""
    create_agent_response = inty_client.api.v1.ai.agents.create(
        name=f"Test Agent",
        gender="MALE",
        visibility="PUBLIC",
    )
    assert create_agent_response.code == 200

    agent_ids_to_cleanup.append(create_agent_response.data.id)

    logger.info(f"create_agent_response: {str(create_agent_response)}")
    test_agent_id = create_agent_response.data.id

    # Prepare request data
    request_data = {
        "messages": [{"role": "user", "content": "Hello, how are you?"}],
        "stream": False,
        "model": "chatbot",
        "language": "en",
    }

    # Make request using the SDK
    response = inty_client.api.v1.chats.create_completion(
        agent_id=test_agent_id, **request_data
    )

    logger.info(f"Chat completion response: {response}")

    # Test that we got a response
    assert response is not None
    assert response.data is not None
