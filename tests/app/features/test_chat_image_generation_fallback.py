"""
Feature test: 聊天生图失败时兜底匹配已生成图片（only_include_ai_character + sent_fallback_images）

通过 API 调用完整流程：主生图失败 → _try_match_existing_image → 返回预置 Resource，
并断言 response 与 chat.sent_fallback_images 更新。使用 in-process 应用与 async db_session，
通过 monkeypatch 触发主生图失败。
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.agent import Agent
from app.models.chat_history import ChatHistory
from app.models.resource import Resource
from app.models.user import User
from app.api import deps
from app.api.v1.endpoints import chat as chat_v1
from app.core.config import global_config_loaded_from_config_yaml
from app.models.agent import AgentStatus, AgentVisibility
from app.models.resource import ResourceType
from app.models.user import AuthType, Gender
from app.schemas.subscription import SubscriptionStatusResponse
from app.schemas.user import User as UserSchema
from app.services import chat_service
from app.services.image_transform_service import image_transform_service


@pytest.fixture
async def db_session():
    """Async DB session，与 test_chat_image_generation 一致，供 seed 与 app 共用。"""
    engine = create_async_engine(
        str(global_config_loaded_from_config_yaml.database.async_url),
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=True,
    )
    async_session = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def app(db_session: AsyncSession):
    """FastAPI 应用：仅挂载 chat 路由，get_async_db 注入同一 db_session。"""
    app = FastAPI()
    app.include_router(chat_v1.router, prefix="/api/v1")

    async def override_get_async_db():
        yield db_session

    app.dependency_overrides[deps.get_async_db] = override_get_async_db
    try:
        yield app
    finally:
        app.dependency_overrides.clear()


class _StubSubscriptionService:
    pass


@pytest.mark.asyncio
async def test_chat_image_generation_fallback_returns_matched_image(
    app: FastAPI,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    """
    主生图失败时走兜底：仅从 only_include_ai_character 的图中按提示词相似度匹配，
    返回预置 Resource 的 CDN URL，并更新 chat.sent_fallback_images。
    """
    # 1) 开启兜底配置
    monkeypatch.setattr(
        global_config_loaded_from_config_yaml.agent,
        "enable_chat_image_match_fallback",
        True,
    )

    # 2) 预置 subscription 限额与用量
    mock_sub = AsyncMock()
    mock_sub.check_image_gen_limit.return_value = (True, 0, 10)
    mock_sub.get_user_subscription_status.return_value = (
        SubscriptionStatusResponse(is_subscribed=False, subscription_status="free")
    )
    mock_sub.record_usage.return_value = None
    subscription_stub = _StubSubscriptionService()
    subscription_stub.check_image_gen_limit = mock_sub.check_image_gen_limit
    subscription_stub.get_user_subscription_status = (
        mock_sub.get_user_subscription_status
    )
    subscription_stub.record_usage = mock_sub.record_usage
    app.dependency_overrides[deps.get_subscription_service] = lambda: subscription_stub

    # 3) 主生图强制失败，触发兜底
    monkeypatch.setattr(
        "app.services.image_generation_service.image_generation_service.generate_chat_image",
        AsyncMock(side_effect=ValueError("simulated primary failure")),
    )

    # 4) Seed：User, Agent, Chat, ChatHistory, Resource
    user_id = f"user-{uuid.uuid4().hex[:8]}"
    agent_id = f"agent-{uuid.uuid4().hex[:8]}"

    user = User(
        id=user_id,
        readable_id=uuid.uuid4().hex[:8],
        auth_type=AuthType.PHONE,
        nickname="Fallback Tester",
        email="fallback@example.com",
        system_language="en",
    )
    db_session.add(user)

    agent = Agent(
        id=agent_id,
        readable_id=uuid.uuid4().hex[:8],
        name="Fallback Agent",
        gender=Gender.FEMALE,
        avatar="https://example.com/avatar.jpg",
        background="https://example.com/background.jpg",
        personality="可爱的女孩",
        scenario="在公园散步",
        intro="intro",
        opening="hello",
        visibility=AgentVisibility.PUBLIC,
        status=AgentStatus.APPROVED,
        creator_id=user_id,
        background_images=[],
    )
    db_session.add(agent)
    await db_session.flush()

    chat = await chat_service.get_or_create_chat_by_agent(
        db=db_session, user_id=user_id, agent_id=agent_id
    )
    await db_session.refresh(chat)

    session_id = chat_service.generate_session_id(chat.id)
    user_msg = ChatHistory(
        session_id=session_id,
        message={"type": "human", "data": {"content": "你好"}},
        meta_data=None,
    )
    db_session.add(user_msg)
    await db_session.flush()

    ai_message_content = "给我画一张图片"
    ai_msg = ChatHistory(
        session_id=session_id,
        message={"type": "ai", "data": {"content": ai_message_content}},
        meta_data=None,
    )
    db_session.add(ai_msg)
    await db_session.commit()
    await db_session.refresh(ai_msg)
    message_id = ai_msg.id

    # Resource：only_include_ai_character=True，generation_prompt 与 build_image_prompt 产出有重叠以便相似度 > 0
    # 使用唯一 URL 避免多次运行或并行时 pk_resources 冲突
    fallback_gcs = f"gs://test-bucket/chat_images/fallback_{uuid.uuid4().hex[:8]}.jpg"
    fallback_prompt = (
        "Create an image character emotional 可爱的女孩 在公园散步 "
        "User request: 给我画一张图片"
    )
    resource = Resource(
        url=fallback_gcs,
        type=ResourceType.IMAGE,
        user_id=user_id,
        agent_id=agent_id,
        resource_metadata={
            "creator": user_id,
            "size": {"width": 64, "height": 64},
            "content_type": "image/jpeg",
            "byte_size": 10,
            "compressed": False,
            "cropped": False,
            "gcs_url": fallback_gcs,
            "generation_prompt": fallback_prompt,
            "only_include_ai_character": True,
        },
    )
    db_session.add(resource)
    await db_session.commit()

    expected_cdn = image_transform_service.transform_desktop(fallback_gcs)

    # 5) 注入当前用户依赖
    async def override_get_current_active_user():
        return UserSchema.model_validate(user)

    app.dependency_overrides[deps.get_current_active_user] = (
        override_get_current_active_user
    )

    # 6) 请求生图
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"/api/v1/chat/images/{agent_id}",
            json={"message_id": message_id},
        )

    # 7) 断言
    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("code") == 200, body
    data = body.get("data", {})
    assert data.get("message_id") == message_id
    assert data.get("image_metadata", {}).get("is_matched") is True
    assert data.get("image_url") == expected_cdn

    # 8) 兜底生图消息 metadata 应包含兜底标记与原始请求文本
    result = await db_session.execute(
        select(ChatHistory).where(ChatHistory.id == message_id)
    )
    updated_msg = result.scalar_one()
    generated_image_meta = (updated_msg.meta_data or {}).get("generated_image", {})
    assert generated_image_meta.get("generation_mode") == "fallback_matched_image"
    assert generated_image_meta.get("original_request") == ai_message_content

    # 9) 可选：兜底图 id 已写入 chat.sent_fallback_images
    await db_session.refresh(chat)
    sent = list(chat.sent_fallback_images or [])
    assert fallback_gcs in sent
