# CREATED_BY_AGENT
"""
Daily bonding memory E2E tests through public APIs.

Flow: insert an undelivered daily_bonding memory row -> call API -> assert
daily_memory_prompt appears and memory.delivery_at is updated.
"""

from datetime import date, datetime, timezone

import pytest
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import global_config_loaded_from_config_yaml
from app.models.memory import Memory
from tests.app.api.test_client import TestClient


@pytest.fixture
def db_session():
    """Provide DB session using backend config database.url."""
    engine = create_engine(global_config_loaded_from_config_yaml.database.url)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _decode_user_id_from_token(token: str) -> str:
    payload = jwt.decode(
        token,
        global_config_loaded_from_config_yaml.security.secret_key,
        algorithms=[global_config_loaded_from_config_yaml.security.algorithm],
    )
    return str(payload["sub"])


def _daily_prompts_for_memory(messages: list, memory_id: int) -> list:
    return [
        m
        for m in messages
        if m.get("type") == "daily_memory_prompt"
        and m.get("daily_memory_id") == memory_id
    ]


def _high_version_headers() -> dict:
    # Use a very high version to satisfy all feature-gating checks.
    return {"appVersionCode": "9999"}


def test_daily_memory_delivered_via_chat_history_api(
    integration_client: TestClient, db_session
):
    agent_id = integration_client.create_agent()
    user_id = _decode_user_id_from_token(integration_client.token)
    local_date = date.today().isoformat()

    memory = Memory(
        user_id=user_id,
        agent_id=agent_id,
        memory_type="daily_bonding",
        content=(
            "Moment: You shared a small win.\n"
            "Meaning: You value steady progress.\n"
            "Next step: Tell me one thing to keep going today."
        ),
        meta_data={
            "local_date": local_date,
            "timezone": "UTC",
            "emotional_salience": 0.7,
            "source_message_count": 12,
        },
        extracted_at=datetime.now(timezone.utc),
        delivery_at=None,
    )
    db_session.add(memory)
    db_session.commit()
    db_session.refresh(memory)
    memory_id = memory.id

    try:
        data = integration_client.get_agent_chat_messages(
            agent_id,
            headers=_high_version_headers(),
        )
        messages = data.get("messages", [])
        daily_prompts = _daily_prompts_for_memory(messages, memory_id)
        assert len(daily_prompts) >= 1, (
            "Expected at least one daily_memory_prompt with matching daily_memory_id, "
            f"got messages={messages}"
        )

        db_session.refresh(memory)
        assert (
            memory.delivery_at is not None
        ), "memory.delivery_at should be set after daily memory delivery"
        assert getattr(memory.delivery_at, "tzinfo", None) is not None
    finally:
        db_session.delete(memory)
        db_session.commit()


def test_daily_memory_chat_completions_appends_daily_prompt_choice(
    integration_client: TestClient, db_session
):
    agent_id = integration_client.create_agent(
        name="Test Daily Memory Prompt Agent",
        gender="MALE",
        visibility="PUBLIC",
    )
    user_id = _decode_user_id_from_token(integration_client.token)
    local_date = date.today().isoformat()

    memory = Memory(
        user_id=user_id,
        agent_id=agent_id,
        memory_type="daily_bonding",
        content=(
            "Moment: We talked about your routine.\n"
            "Meaning: Consistency calms you down.\n"
            "Next step: Share one small routine for tonight."
        ),
        meta_data={
            "local_date": local_date,
            "timezone": "UTC",
            "emotional_salience": 0.6,
            "source_message_count": 9,
        },
        extracted_at=datetime.now(timezone.utc),
        delivery_at=None,
    )
    db_session.add(memory)
    db_session.commit()
    db_session.refresh(memory)
    memory_id = memory.id

    try:
        response = integration_client.chat_completions(
            agent_id,
            [{"role": "user", "content": "Hi"}],
            language="en",
            headers=_high_version_headers(),
        )
        assert response.get("code") == 200, response
        choices = response.get("data", {}).get("choices", [])
        daily_choices = [
            c
            for c in choices
            if c.get("message", {}).get("type") == "daily_memory_prompt"
            and c.get("message", {}).get("daily_memory_id") == memory_id
        ]
        assert len(daily_choices) >= 1, (
            "Expected at least one daily_memory_prompt choice with matching id, "
            f"got choices={choices}"
        )
        message = daily_choices[0].get("message", {})
        assert isinstance(message.get("id"), int)

        db_session.refresh(memory)
        assert (
            memory.delivery_at is not None
        ), "memory.delivery_at should be set after chat completions delivery"
    finally:
        db_session.delete(memory)
        db_session.commit()


def test_daily_memory_agent_detail_includes_daily_memories(
    integration_client: TestClient, db_session
):
    agent_id = integration_client.create_agent()
    user_id = _decode_user_id_from_token(integration_client.token)
    local_date = date.today().isoformat()

    memory = Memory(
        user_id=user_id,
        agent_id=agent_id,
        memory_type="daily_bonding",
        content=(
            "Moment: You checked in after work.\n"
            "Meaning: You are trying to stay emotionally present.\n"
            "Next step: Tell me one thing you want to unwind with."
        ),
        meta_data={
            "local_date": local_date,
            "timezone": "UTC",
            "emotional_salience": 0.5,
            "source_message_count": 8,
        },
        extracted_at=datetime.now(timezone.utc),
        delivery_at=None,
    )
    db_session.add(memory)
    db_session.commit()
    db_session.refresh(memory)
    memory_id = memory.id

    try:
        data = integration_client.get_agent(
            agent_id,
            headers=_high_version_headers(),
        )
        features = data.get("features") or {}
        daily_list = features.get("daily_memories") or []
        matched = [
            item for item in daily_list if item.get("memory_id") == memory_id
        ]
        assert (
            len(matched) == 1
        ), f"Expected daily memory in agent features, got daily_memories={daily_list}"
    finally:
        db_session.delete(memory)
        db_session.commit()


def test_daily_memory_agent_detail_gated_by_app_version_when_threshold_enabled(
    integration_client: TestClient, db_session
):
    min_ver = (
        global_config_loaded_from_config_yaml.app.min_app_version_code_for_daily_memory
    )
    if min_ver == 0:
        pytest.skip("daily memory min version is 0, gate is not enabled")

    agent_id = integration_client.create_agent()
    user_id = _decode_user_id_from_token(integration_client.token)
    local_date = date.today().isoformat()

    memory = Memory(
        user_id=user_id,
        agent_id=agent_id,
        memory_type="daily_bonding",
        content=(
            "Moment: You shared your plan.\n"
            "Meaning: You are investing in long-term stability.\n"
            "Next step: Share one concrete action for tomorrow."
        ),
        meta_data={
            "local_date": local_date,
            "timezone": "UTC",
        },
        extracted_at=datetime.now(timezone.utc),
        delivery_at=None,
    )
    db_session.add(memory)
    db_session.commit()

    try:
        high = integration_client.get_agent(
            agent_id,
            headers={"appVersionCode": str(min_ver)},
        )
        high_features = high.get("features") or {}
        assert len(high_features.get("daily_memories") or []) >= 1

        low = integration_client.get_agent(
            agent_id,
            headers={"appVersionCode": str(min_ver - 1)},
        )
        low_features = low.get("features") or {}
        assert len(low_features.get("daily_memories") or []) == 0
    finally:
        db_session.delete(memory)
        db_session.commit()
