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
    return Inty(
        base_url="http://localhost:8000",  # Adjust if your dev server runs on different port
        api_key="test-api-key",  # This will be replaced with actual auth
    )

@pytest.fixture
def app():
    """Launch the app locally using uvicorn."""
    import subprocess
    import threading
    import time

    from app.main import app

    # Start uvicorn server in a separate process
    process = subprocess.Popen([
        "uvicorn", 
        "app.main:app", 
        "--host", "127.0.0.1", 
        "--port", "8000",
        "--log-level", "warning"  # Reduce log noise during tests
    ])
    
    # Wait for server to start
    time.sleep(2)
    
    try:
        yield app
    finally:
        # Clean up: terminate the uvicorn process
        process.terminate()
        process.wait()


def test_agent_chat_completions_with_sdk(inty_client):
    """Test chat completions using the Python SDK."""
    # Prepare request data
    request_data = {
        "messages": [{"role": "user", "content": "Hello, how are you?"}],
        "stream": False,
        "model": "chatbot",
        "language": "en",
    }

    # Create a test agent ID
    test_agent_id = "test-agent-123"

    # Make request using the SDK
    response = inty_client.api.v1.chats.create_completion(
        agent_id=test_agent_id,
        **request_data
    )
    
    logger.info(f"SDK response: {response}")
    
    # Test that we got a response
    assert response is not None
    
    # If successful, check response structure
    if hasattr(response, 'data'):
        assert response.data is not None
