import httpx
import pytest


@pytest.mark.noci
def test_chat_completions_endpoint():
    """Test the chat completions endpoint with a valid request"""

    # Headers (you'll need to provide a valid token)
    BEARER_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjA5MjMyOTAsInN1YiI6InVzZXItdGVzdGluZyJ9.TS3IaZ8UKeC9sbGn513m66aDXdLLrFsHYYNW9X0vCcA"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {BEARER_TOKEN}",
    }

    # First, create an agent
    create_agent_url = "http://localhost:8000/api/v1/ai/agents"
    agent_payload = {
        "name": "Test Agent",
        "gender": "FEMALE",
        "visibility": "PRIVATE",
        "intro": "This is a test AI agent",
        "opening": "Hello! I am your AI assistant.",
        "personality": "Friendly and helpful",
        "scenario": "A helpful AI assistant for testing",
    }

    with httpx.Client(timeout=30.0) as client:
        # Create agent
        create_response = client.post(
            create_agent_url, json=agent_payload, headers=headers
        )
        assert (
            create_response.status_code == 200
        ), f"Agent creation failed: {create_response.text}"

        create_data = create_response.json()
        assert (
            create_data["code"] == 200
        ), f"Agent creation returned error: {create_data}"
        agent_id = create_data["data"]["id"]

        # Now test chat completions with the created agent
        chat_url = f"http://localhost:8000/api/v2/chat/completions/{agent_id}"
        chat_payload = {
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "model": "gpt-4",
            "language": "en",
            "stream": False,
        }

        response = client.post(chat_url, json=chat_payload, headers=headers)

    # Assertions
    assert response.status_code == 200, f"Chat completion failed: {response.text}"

    # Parse response
    response_data = response.json()

    # Check response structure
    assert "code" in response_data
    assert "message" in response_data
    assert "data" in response_data

    # Check that code is 200 (success)
    assert response_data["code"] == 200

    # Check data structure matches ChatCompletionResponse
    data = response_data["data"]
    assert "id" in data
    assert "created" in data
    assert "model" in data
    assert "choices" in data
    assert "usage" in data

    # Check choices structure
    assert isinstance(data["choices"], list)
    assert len(data["choices"]) == 1

    choice = data["choices"][0]
    assert "index" in choice
    assert "message" in choice
    assert "finish_reason" in choice

    # Check message structure
    message = choice["message"]
    assert "role" in message
    assert "content" in message
    assert message["role"] == "assistant"
    assert isinstance(message["content"], str)
    assert len(message["content"]) > 0
    # assert message["content"] == "I'm wonderful now that you're here, admin."
    # Content keeps changing, so we don't check it.

    # Check usage structure
    usage = data["usage"]
    assert "prompt_tokens" in usage
    assert "completion_tokens" in usage
    assert "total_tokens" in usage
    assert isinstance(usage["prompt_tokens"], int)
    assert isinstance(usage["completion_tokens"], int)
    assert isinstance(usage["total_tokens"], int)

    # Check that total_tokens equals sum of prompt and completion tokens
    assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]
