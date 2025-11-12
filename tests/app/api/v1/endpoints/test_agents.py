import uuid

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


def test_text_to_image_endpoint(integration_client: TestClient):
    image_urls = integration_client.text_to_image(
        "A warm portrait of a friendly companion, soft lighting, vivid colors",
        count=1,
    )

    assert image_urls
    assert all(url.startswith("http") for url in image_urls)


def test_create_agent_without_background_returns_null(integration_client: TestClient):
    payload = {
        "name": f"No Background Agent {uuid.uuid4().hex[:6]}",
        "gender": "FEMALE",
        "visibility": "PRIVATE",
        "personality": "Keeps conversation light and fun",
        "scenario": "Helps with background-free testing",
    }

    response = integration_client.client.post(
        f"{API_BASE_URL}/api/v1/ai/agents",
        json=payload,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("code") == 200, body

    agent_data = body.get("data") or {}
    agent_id = agent_data.get("id")
    assert agent_id, "agent id should be present in create response"

    try:
        assert agent_data.get("background") is None
        assert agent_data.get("background_images") == []

        detail_response = integration_client.client.get(
            f"{API_BASE_URL}/api/v1/ai/agents/{agent_id}"
        )
        assert detail_response.status_code == 200, detail_response.text
        detail_data = detail_response.json()

        assert detail_data.get("background") is None
        assert detail_data.get("background_images") == []
    finally:
        integration_client.delete_agent(agent_id)
