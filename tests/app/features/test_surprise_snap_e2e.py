# CREATED_BY_AGENT
"""
Surprise Snap 端到端测试：聊天 choice、消息列表、解锁接口及异常场景。

依赖本地后端 (localhost:8000) 与 config.yaml（含 surprise_snap 配置，如 devops/config.yaml.test）。
"""

import pytest
from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker

from app.core.config import global_config_loaded_from_config_yaml
from app.models.agent import Agent
from tests.app.api.test_client import TestClient


@pytest.fixture
def db_session():
    """提供数据库会话，与后端共用 config.yaml 的 database.url。"""
    engine = create_engine(global_config_loaded_from_config_yaml.database.url)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _surprise_snap_enabled():
    return global_config_loaded_from_config_yaml.surprise_snap.enabled_since is not None


def _set_agent_exclusive_photos(db_session, agent_id: str, photos: list):
    """在 DB 中设置 agent 的 exclusive_photos（App API 不暴露该字段）。"""
    # Core update：create_agent 等请求已在服务端更新过 Agent.version，ORM flush 会带旧
    # version 条件导致 StaleDataError。
    result = db_session.execute(
        update(Agent).where(Agent.id == agent_id).values(exclusive_photos=photos)
    )
    assert result.rowcount == 1, f"Agent {agent_id} not found"
    db_session.commit()


def _choices_with_surprise_snap(choices: list):
    """返回 choices 中 message.type == surprise_snap 的项。"""
    return [
        c
        for c in choices
        if c.get("message", {}).get("type") == "surprise_snap"
    ]


def _messages_with_surprise_snap(messages: list):
    """返回消息列表中 type == surprise_snap 的项。"""
    return [m for m in messages if m.get("type") == "surprise_snap"]


def test_chat_completions_returns_surprise_snap_choice_when_triggered(
    integration_client: TestClient, db_session
):
    """触发时响应 choices 中含一条 surprise_snap，且含 id、media_url、caption、price、is_locked。"""
    if not _surprise_snap_enabled():
        pytest.skip("surprise_snap not enabled")

    agent_id = integration_client.create_agent()
    _set_agent_exclusive_photos(
        db_session,
        agent_id,
        [
            {
                "image_url": "https://example.com/e2e.jpg",
                "caption": "E2E",
                "credits_required": 1,
            }
        ],
    )

    response = integration_client.chat_completions(
        agent_id,
        [{"role": "user", "content": "Hi"}],
    )
    assert response.get("code") == 200, response
    data = response.get("data", {})
    choices = data.get("choices", [])
    assert len(choices) >= 2, f"Expected at least 2 choices (AI + surprise_snap), got {len(choices)}"

    snap_choices = _choices_with_surprise_snap(choices)
    assert len(snap_choices) >= 1, f"Expected at least one surprise_snap choice, got choices={choices}"
    msg = snap_choices[0]["message"]
    assert msg.get("type") == "surprise_snap"
    assert "id" in msg
    assert "media_url" in msg
    assert "caption" in msg
    assert "price" in msg
    assert "is_locked" in msg
    assert msg["is_locked"] is True


def test_get_agent_messages_includes_surprise_snap_with_is_locked(
    integration_client: TestClient, db_session
):
    """GET messages 列表中含 surprise_snap 消息，且 is_locked 为 True（免费用户）。"""
    if not _surprise_snap_enabled():
        pytest.skip("surprise_snap not enabled")

    agent_id = integration_client.create_agent()
    _set_agent_exclusive_photos(
        db_session,
        agent_id,
        [
            {
                "image_url": "https://example.com/e2e2.jpg",
                "caption": "E2E messages",
                "credits_required": 2,
            }
        ],
    )
    integration_client.chat_completions(
        agent_id,
        [{"role": "user", "content": "Hello"}],
    )

    data = integration_client.get_agent_chat_messages(agent_id)
    messages = data.get("messages", [])
    snap_msgs = _messages_with_surprise_snap(messages)
    assert len(snap_msgs) >= 1, f"Expected at least one surprise_snap in messages, got {messages}"
    m = snap_msgs[0]
    assert "media_url" in m
    assert "caption" in m
    assert "price" in m
    assert m.get("is_locked") is True


def test_surprise_snap_unlock_success(
    integration_client: TestClient, db_session
):
    """POST unlock 返回 200；再次 GET messages 该条 is_locked 为 False。"""
    if not _surprise_snap_enabled():
        pytest.skip("surprise_snap not enabled")

    agent_id = integration_client.create_agent()
    _set_agent_exclusive_photos(
        db_session,
        agent_id,
        [
            {
                "image_url": "https://example.com/unlock.jpg",
                "caption": "Unlock",
                "credits_required": 1,
            }
        ],
    )
    response = integration_client.chat_completions(
        agent_id,
        [{"role": "user", "content": "One"}],
    )
    choices = response["data"]["choices"]
    snap_choices = _choices_with_surprise_snap(choices)
    assert len(snap_choices) >= 1
    message_id = snap_choices[0]["message"]["id"]

    unlock_resp = integration_client.surprise_snap_unlock(message_id)
    assert unlock_resp.status_code == 200, unlock_resp.text
    body = unlock_resp.json()
    assert body.get("data", {}).get("unlocked") is True

    data = integration_client.get_agent_chat_messages(agent_id)
    snap_msgs = _messages_with_surprise_snap(data.get("messages", []))
    assert len(snap_msgs) >= 1
    assert snap_msgs[0].get("is_locked") is False


def test_surprise_snap_unlock_idempotent(
    integration_client: TestClient, db_session
):
    """对同一 message_id 调用两次 unlock，两次均返回 200。"""
    if not _surprise_snap_enabled():
        pytest.skip("surprise_snap not enabled")

    agent_id = integration_client.create_agent()
    _set_agent_exclusive_photos(
        db_session,
        agent_id,
        [
            {
                "image_url": "https://example.com/idem.jpg",
                "caption": "Idem",
                "credits_required": 1,
            }
        ],
    )
    integration_client.chat_completions(
        agent_id,
        [{"role": "user", "content": "Idem"}],
    )
    data = integration_client.get_agent_chat_messages(agent_id)
    snap_msgs = _messages_with_surprise_snap(data.get("messages", []))
    assert len(snap_msgs) >= 1
    message_id = snap_msgs[0]["id"]

    r1 = integration_client.surprise_snap_unlock(message_id)
    r2 = integration_client.surprise_snap_unlock(message_id)
    assert r1.status_code == 200, r1.text
    assert r2.status_code == 200, r2.text


def test_surprise_snap_unlock_invalid_returns_403(
    integration_client: TestClient, db_session
):
    """用非 surprise_snap 的消息 ID（普通 AI 消息 id）调用 unlock，返回 403。"""
    agent_id = integration_client.create_agent()
    response = integration_client.chat_completions(
        agent_id,
        [{"role": "user", "content": "Just AI reply"}],
    )
    choices = response["data"]["choices"]
    assert len(choices) >= 1
    ai_message_id = choices[0]["message"]["id"]

    unlock_resp = integration_client.surprise_snap_unlock(ai_message_id)
    assert unlock_resp.status_code == 403, unlock_resp.text


def test_chat_completions_no_surprise_snap_choice_when_agent_has_no_exclusive_photos(
    integration_client: TestClient, db_session
):
    """Agent 无 exclusive_photos 时发消息，仅 1 个 choice（AI 回复），无 surprise_snap。"""
    if not _surprise_snap_enabled():
        pytest.skip("surprise_snap not enabled")

    agent_id = integration_client.create_agent()
    _set_agent_exclusive_photos(db_session, agent_id, [])

    response = integration_client.chat_completions(
        agent_id,
        [{"role": "user", "content": "No photo"}],
    )
    assert response.get("code") == 200, response
    choices = response.get("data", {}).get("choices", [])
    assert len(choices) == 1, f"Expected single AI choice, got {len(choices)}"
    assert choices[0].get("message", {}).get("type") != "surprise_snap"
    snap_choices = _choices_with_surprise_snap(choices)
    assert len(snap_choices) == 0
