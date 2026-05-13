import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import global_config_loaded_from_config_yaml
from app.models.chat import Chat
from app.models.chat_history import ChatHistory
from app.models.subscription import SubscriptionStatus, UserSubscription
from app.services.chat_service import generate_session_id
from tests.app.api.test_client import TestClient


def _create_db_session():
    engine = create_engine(global_config_loaded_from_config_yaml.database.url)
    Session = sessionmaker(bind=engine)
    return Session()


def _get_current_user_id(integration_client: TestClient) -> str:
    response = integration_client.client.get(
        f"{integration_client.base_url}/api/v1/users/me"
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["code"] == 200
    return payload["data"]["id"]


def _seed_chat_message(
    *,
    db_session,
    user_id: str,
    agent_id: str,
    message: dict,
) -> tuple[str, int]:
    chat_id = f"chat-{uuid.uuid4().hex}"
    chat = Chat(
        id=chat_id,
        user_id=user_id,
        agent_id=agent_id,
        is_active=True,
    )
    db_session.add(chat)
    db_session.commit()

    session_id = uuid.UUID(generate_session_id(chat_id))
    chat_message = ChatHistory(
        session_id=session_id,
        message=message,
    )
    db_session.add(chat_message)
    db_session.commit()
    db_session.refresh(chat_message)
    return chat_id, chat_message.id


def _cleanup_seeded_chat(db_session, chat_id: str) -> None:
    session_id = uuid.UUID(generate_session_id(chat_id))
    db_session.query(ChatHistory).filter(ChatHistory.session_id == session_id).delete()
    db_session.query(Chat).filter(Chat.id == chat_id).delete()
    db_session.commit()


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

    integration_client.untrack_agent(agent_id)


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


def test_clear_messages_success_e2e(integration_client: TestClient):
    agent_id = integration_client.create_agent(
        name=f"clear-messages-{uuid.uuid4().hex[:6]}",
        visibility="PUBLIC",
    )

    try:
        messages_response = integration_client.client.get(
            f"{integration_client.base_url}/api/v1/chats/agents/{agent_id}/messages",
            params={"limit": 20, "offset": 0, "order": "desc"},
        )
        assert messages_response.status_code == 200, messages_response.text

        response = integration_client.client.post(
            f"{integration_client.base_url}/api/v1/chats/agents/{agent_id}/clear-messages",
            json={},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["success"] is True
        assert payload["deleted_count"] >= 0
    finally:
        integration_client.delete_agent(agent_id)


def test_vote_message_success_e2e(integration_client: TestClient):
    agent_id = integration_client.create_agent(
        name=f"vote-message-{uuid.uuid4().hex[:6]}",
        visibility="PUBLIC",
    )
    db_session = _create_db_session()
    user_id = _get_current_user_id(integration_client)
    chat_id, message_id = _seed_chat_message(
        db_session=db_session,
        user_id=user_id,
        agent_id=agent_id,
        message={"type": "ai", "data": {"content": "seed vote target"}},
    )

    try:
        response = integration_client.client.post(
            f"{integration_client.base_url}/api/v1/chats/messages/vote",
            json={"agent_id": agent_id, "message_id": message_id, "vote": "like"},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["code"] == 200
        assert payload["data"]["vote"] == "like"
    finally:
        _cleanup_seeded_chat(db_session, chat_id)
        db_session.close()
        integration_client.delete_agent(agent_id)


def test_subscription_verify_success_e2e(integration_client: TestClient):
    plans_response = integration_client.client.get(
        f"{integration_client.base_url}/api/v1/subscription/plans"
    )
    assert plans_response.status_code == 200, plans_response.text
    plans_payload = plans_response.json()
    assert plans_payload["code"] == 200
    plans = plans_payload["data"]["plans"]
    assert len(plans) > 0
    product_id = plans[0]["google_play_product_id"]
    purchase_token = f"e2e-subscription-token-{uuid.uuid4().hex}"
    order_id = f"e2e-order-{uuid.uuid4().hex[:10]}"
    user_id = _get_current_user_id(integration_client)

    response = integration_client.client.post(
        f"{integration_client.base_url}/api/v1/subscription/verify",
        json={
            "product_id": product_id,
            "purchase_token": purchase_token,
            "order_id": order_id,
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["code"] == 200
    assert payload["data"]["is_verified"] is True

    db_session = _create_db_session()
    try:
        db_session.query(UserSubscription).filter(
            UserSubscription.user_id == user_id
        ).update(
            {
                "status": SubscriptionStatus.CANCELLED,
                "end_date": datetime.now(timezone.utc) - timedelta(minutes=1),
                "auto_renew": False,
            },
            synchronize_session=False,
        )
        db_session.commit()
    finally:
        db_session.close()


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
