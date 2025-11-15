"""Integration tests for chat endpoints using the custom TestClient."""

import pytest
from loguru import logger

from tests.app.api.test_client import TestClient


@pytest.fixture(scope="function")
def agent_ids_to_cleanup(integration_client: TestClient):
    agent_ids = []
    yield agent_ids
    for agent_id in agent_ids:
        logger.info(f"Deleting agent: {agent_id}")
        integration_client.delete_agent(agent_id)
        logger.info(f"Deleted agent: {agent_id}")


@pytest.mark.noci
def test_agent_chat_completions_with_sdk(
    integration_client: TestClient, agent_ids_to_cleanup
):
    """Test chat completions using the custom TestClient."""
    agent_id = integration_client.create_agent(
        name="Test Agent",
        gender="MALE",
        visibility="PUBLIC",
    )
    agent_ids_to_cleanup.append(agent_id)

    messages = [{"role": "user", "content": "Hello, how are you?"}]

    response = integration_client.chat_completions(
        agent_id,
        messages,
        language="en",
    )

    logger.info(f"Chat completion response: {response}")

    assert response is not None
    assert response.get("code") == 200
    assert response.get("data") is not None
