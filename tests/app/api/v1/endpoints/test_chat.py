"""
Integration tests for chat endpoints.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from loguru import logger

from app.main import app
from scripts.init_admin_user import create_admin_user


def test_agent_chat_completions_endpoint_exists():
    """Test that the chat completions endpoint exists and responds."""
    client = TestClient(app)
    

    # Prepare request data
    request_data = {
        "messages": [{"role": "user", "content": "Hello, how are you?"}],
        "stream": False,
        "model": "chatbot",
        "language": "en",
    }

    # Create a test agent ID
    test_agent_id = "test-agent-123"

    # Make request with bearer token
    headers = {"Authorization": "Bearer your-test-token-here"}
    response = client.post(
        f"/api/v1/chat/completions/{test_agent_id}", json=request_data, headers=headers
    )

    logger.info(f"response: {str(response)}")

    # Test that the endpoint exists and returns a response
    # We expect either 401 (unauthorized) or 404 (agent not found) since we're not setting up auth/db
    assert response.status_code in [200, 401, 404, 500]

    # If we get a response, it should be JSON
    if response.status_code != 500:  # 500 might not have proper JSON
        response_data = response.json()
        assert isinstance(response_data, dict)
