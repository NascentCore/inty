import httpx
import pytest


@pytest.mark.noci
def test_chat_completions_endpoint():
    """Test the chat completions endpoint with a valid request"""
# 标头（您需要 provid 一个有效的令牌）
    BEARER_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjA5MjMyOTAsInN1YiI6InVzZXItdGVzdGluZyJ9.TS3IaZ8UKeC9sbGn513m66aDXdLLrFsHYYNW9X0vCcA"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {BEARER_TOKEN}",
    }
#首先创建一个代理
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
#创建代理
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
# 现在完成使用创建的代理测试聊天情况
        chat_url = f"http://localhost:8000/api/v2/chat/completions/{agent_id}"
        chat_payload = {
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "model": "gpt-4",
            "language": "en",
            "stream": False,
        }

        response = client.post(chat_url, json=chat_payload, headers=headers)
#断言
    assert response.status_code == 200, f"Chat completion failed: {response.text}"
# 解析响应
    response_data = response.json()
#检查响应结构
    assert "code" in response_data
    assert "message" in response_data
    assert "data" in response_data
#检查代码是否为200（成功）
    assert response_data["code"] == 200
# 检查数据结构是否匹配ChatCompletionResponse
    data = response_data["data"]
    assert "id" in data
    assert "created" in data
    assert "model" in data
    assert "choices" in data
    assert "usage" in data
#检查选择结构
    assert isinstance(data["choices"], list)
    assert len(data["choices"]) == 1

    choice = data["choices"][0]
    assert "index" in choice
    assert "message" in choice
    assert "finish_reason" in choice
#检查消息结构
    message = choice["message"]
    assert "role" in message
    assert "content" in message
    assert message["role"] == "assistant"
    assert isinstance(message["content"], str)
    assert len(message["content"]) > 0
#断言消息[“内容”] ==“管理员，你现在在这里我真是太棒了。”
# 内容不断变化，所以我们不检查。
# 检查使用结构
    usage = data["usage"]
    assert "prompt_tokens" in usage
    assert "completion_tokens" in usage
    assert "total_tokens" in usage
    assert isinstance(usage["prompt_tokens"], int)
    assert isinstance(usage["completion_tokens"], int)
    assert isinstance(usage["total_tokens"], int)
# 检查total_tokens是否足够prompt并完成标记的总和
    assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]
