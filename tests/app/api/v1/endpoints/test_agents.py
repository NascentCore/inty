import pytest

from tests.app.api.test_client import TestClient

API_BASE_URL = "http://localhost:8000"


@pytest.fixture
def integration_client():
    client = TestClient(API_BASE_URL)
    client.create_user()
    try:
        yield client
    finally:
        client.delete_user()
        client.close()


def test_chat_completions_endpoint(integration_client: TestClient):
    agent_id = integration_client.create_agent()

    response = integration_client.chat_completions(
        agent_id,
        messages=[
            {"role": "user", "content": "Tell me a fun fact about penguins."}
        ],
        language="en",
    )

    assert response["code"] == 200
    data = response["data"]
    assert data["model"] == "chatbot"
    assert isinstance(data["created"], int)

    choices = data["choices"]
    assert isinstance(choices, list) and choices

    message = choices[0]["message"]
    assert message["role"] == "assistant"
    assert isinstance(message["content"], str)
    assert message["content"].strip()

    usage = data["usage"]
    assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]


@pytest.mark.noci
def test_text_to_image_endpoint(integration_client: TestClient):
    image_urls = integration_client.text_to_image(
        "A warm portrait of a friendly companion, soft lighting, vivid colors",
        count=1,
    )

    assert image_urls
    assert all(url.startswith("http") for url in image_urls)


@pytest.mark.parametrize("background", ["", None])
def test_create_agent_with_empty_background(
    integration_client: TestClient, background: str
):

    # 测试数据：background 为空字符串
    agent_data = {
        "name": "Test Agent Empty Background",
        "gender": "FEMALE",
        "visibility": "PRIVATE",
        "personality": "一个友好的测试角色",
        "scenario": "用于测试空背景字段的场景",
        "intro": "这是一个测试角色",
        "opening": "你好！我是用来测试空背景的角色。",
        "background": background,
    }

    # 发送创建请求
    response = integration_client.client.post(
        f"{integration_client.base_url}/api/v1/ai/agents",
        json=agent_data,
        headers={"Authorization": f"Bearer {integration_client.token}"},
    )

    # 验证响应
    assert response.status_code == 200, f"Request failed: {response.text}"

    response_data = response.json()
    assert response_data.get("code") == 200, f"API error: {response_data}"

    # 验证创建的 agent 数据
    agent = response_data["data"]
    assert agent["name"] == agent_data["name"]
    assert agent["gender"] == agent_data["gender"]
    assert agent["visibility"] == agent_data["visibility"]
    assert agent["personality"] == agent_data["personality"]
    assert agent["scenario"] == agent_data["scenario"]

    # 关键验证：background 为空字符串时的实际行为
    # 由于 process_agent_image_urls 中的条件 `if processed_data.get("background"):`
    # 对空字符串返回 False，验证代码块被跳过，空字符串被保留
    assert (
        agent["background"] == background
    ), f"Expected background to be {background}, but got: {agent['background']}"

    # 验证 agent 有唯一 ID
    assert agent["id"]
    assert agent["readable_id"]

    # 清理：删除创建的 agent
    integration_client.delete_agent(agent["id"])
