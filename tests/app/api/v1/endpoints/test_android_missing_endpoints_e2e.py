import uuid

from tests.app.api.test_client import TestClient


def test_get_user_created_agents_e2e(integration_client: TestClient):
    response = integration_client.client.get(
        f"{integration_client.base_url}/api/v1/ai/agents/me",
        params={"skip": 0, "limit": 20},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["code"] == 200
    assert isinstance(payload["data"], list)


def test_get_agent_detail_e2e(integration_client: TestClient):
    agent_id = integration_client.create_agent(
        name=f"get-agent-detail-{uuid.uuid4().hex[:6]}",
        visibility="PUBLIC",
    )

    try:
        response = integration_client.client.get(
            f"{integration_client.base_url}/api/v1/ai/agents/{agent_id}"
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["id"] == agent_id
    finally:
        integration_client.delete_agent(agent_id)


def test_delete_agent_e2e(integration_client: TestClient):
    agent_id = integration_client.create_agent(
        name=f"delete-agent-{uuid.uuid4().hex[:6]}",
        visibility="PUBLIC",
    )

    response = integration_client.client.delete(
        f"{integration_client.base_url}/api/v1/ai/agents/{agent_id}"
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["code"] == 200
    assert payload["data"]["id"] == agent_id

    if agent_id in integration_client._created_agents:
        integration_client._created_agents.remove(agent_id)


def test_list_character_themes_e2e(integration_client: TestClient):
    response = integration_client.client.get(
        f"{integration_client.base_url}/api/v1/character-themes/",
        params={"skip": 0, "limit": 20},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["code"] == 200
    assert isinstance(payload["data"], list)


def test_list_chats_e2e(integration_client: TestClient):
    response = integration_client.client.get(
        f"{integration_client.base_url}/api/v1/chats/",
        params={"skip": 0, "limit": 20},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert isinstance(payload, list)


def test_get_subscription_plans_e2e(integration_client: TestClient):
    response = integration_client.client.get(
        f"{integration_client.base_url}/api/v1/subscription/plans"
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["code"] == 200
    assert "plans" in payload["data"]


def test_list_text_to_speech_voices_e2e(integration_client: TestClient):
    response = integration_client.client.get(
        f"{integration_client.base_url}/api/v1/text-to-speech/list-voices",
        params={"provider": "gemini", "page_size": 10},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) > 0
    assert all(item.get("provider") == "gemini" for item in payload)


def test_google_login_with_invalid_token_e2e(integration_client: TestClient):
    response = integration_client.client.post(
        f"{integration_client.base_url}/api/v1/auth/google/login",
        json={"id_token": "invalid-token-for-e2e-test"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert "code" in payload
    assert payload["code"] != 200
    assert payload.get("message")


def test_clear_messages_without_chat_session_e2e(integration_client: TestClient):
    agent_id = integration_client.create_agent(
        name=f"clear-messages-{uuid.uuid4().hex[:6]}",
        visibility="PUBLIC",
    )

    try:
        response = integration_client.client.post(
            f"{integration_client.base_url}/api/v1/chats/agents/{agent_id}/clear-messages",
            json={},
        )
        assert response.status_code == 404, response.text
        payload = response.json()
        assert "detail" in payload
    finally:
        integration_client.delete_agent(agent_id)


def test_vote_message_missing_message_e2e(integration_client: TestClient):
    agent_id = integration_client.create_agent(
        name=f"vote-message-{uuid.uuid4().hex[:6]}",
        visibility="PUBLIC",
    )

    try:
        response = integration_client.client.post(
            f"{integration_client.base_url}/api/v1/chats/messages/vote",
            json={"agent_id": agent_id, "message_id": 999999, "vote": "like"},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["code"] == 404
        assert "Message not found" in payload["message"]
    finally:
        integration_client.delete_agent(agent_id)


def test_surprise_snap_unlock_missing_message_e2e(integration_client: TestClient):
    response = integration_client.client.post(
        f"{integration_client.base_url}/api/v1/chats/surprise-snap/unlock",
        json={"message_id": 999999},
    )

    assert response.status_code == 403, response.text
    payload = response.json()
    assert "detail" in payload


def test_subscription_verify_with_fake_payload_e2e(integration_client: TestClient):
    response = integration_client.client.post(
        f"{integration_client.base_url}/api/v1/subscription/verify",
        json={
            "product_id": "test.product.monthly",
            "purchase_token": "fake_purchase_token",
            "order_id": "fake_order_id",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert "code" in payload
    assert "message" in payload


def test_update_user_profile_e2e(integration_client: TestClient):
    nickname = f"updated-{uuid.uuid4().hex[:6]}"
    response = integration_client.client.put(
        f"{integration_client.base_url}/api/v1/users/profile",
        json={"nickname": nickname},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["code"] == 200
    assert payload["data"]["nickname"] == nickname
