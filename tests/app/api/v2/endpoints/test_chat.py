import httpx
import pytest


def test_chat_completions_endpoint():
    """Test the chat completions endpoint with a valid request"""

    # Test data
    agent_id = "test-agent-123"
    url = f"http://localhost:8000/api/v2/chat/completions/{agent_id}"
    
    # Request payload
    payload = {
        "messages": [
            {
                "role": "user",
                "content": "Hello, how are you?"
            }
        ],
        "model": "gpt-4",
        "language": "en",
        "stream": False
    }
    
    # Headers (you'll need to provide a valid token)
    BEARER_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjA4OTkxNTksInN1YiI6InVzZXItMDFKV1ozNFk0RDFDOTJHRDg2QTVSNkVXWUoifQ.kn3jrJeJZ03XOXbiVtzs71f_8_I0WO183ok3dVrm7xg"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {BEARER_TOKEN}"
    }
    
    # Make the request
    with httpx.Client() as client:
        response = client.post(url, json=payload, headers=headers)
    
    # Assertions
    assert response.status_code == 200
    
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
    assert "object" in data
    assert "created" in data
    assert "model" in data
    assert "choices" in data
    assert "usage" in data
    
    # Check object type
    assert data["object"] == "chat.completion"
    
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
