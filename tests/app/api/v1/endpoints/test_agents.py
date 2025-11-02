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


@pytest.mark.noci
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
    try:
        image_urls = integration_client.text_to_image(
            "A warm portrait of a friendly companion, soft lighting, vivid colors",
            count=1,
        )

        assert image_urls
        assert all(url.startswith("http") for url in image_urls)
    except RuntimeError as e:
        # Guest users are not allowed to generate images, skip test if limit reached
        if "Image generation limit reached" in str(e):
            pytest.skip(
                f"Skipping test: Guest user image generation limit reached. "
                f"Error: {e}"
            )
        raise
