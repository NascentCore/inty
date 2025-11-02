"""
测试聊天服务功能
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.core.config import global_config_loaded_from_config_yaml
from app.models.agent import AgentStatus, AgentVisibility
from app.models.user import AuthType, Gender
from app.schemas.chat import ChatImageGenerationResponse
from app.services import chat_service


@pytest.fixture
async def db_session():
    """提供数据库会话用于测试"""
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


class TestChatService:
    """测试聊天服务"""

    @pytest.mark.asyncio
    @patch("app.services.chat_service.subscription_service.record_usage")
    @patch("app.services.image_generation_service.image_generation_service.generate_chat_image_with_gemini")
    @patch("app.services.chat_service.subscription_service.check_image_gen_limit")
    async def test_generate_chat_image_success(
        self,
        mock_check_limit: AsyncMock,
        mock_generate_image: AsyncMock,
        mock_record_usage: AsyncMock,
        db_session: AsyncSession,
    ):
        """测试生成聊天图片成功流程 - 使用真实数据库"""
        # 准备测试数据
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        agent_id = f"test_agent_{uuid.uuid4().hex[:8]}"
        history_count = 10

        # 创建测试用户
        test_user = models.User(
            id=user_id,
            readable_id=str(uuid.uuid4().int)[:8],
            auth_type=AuthType.PHONE,
            nickname="Test User",
            email="test@example.com",
            system_language="en",
            is_active=True,
        )
        db_session.add(test_user)
        await db_session.commit()
        await db_session.refresh(test_user)

        # 创建测试 Agent
        test_agent = models.Agent(
            id=agent_id,
            readable_id=str(uuid.uuid4().int)[:8],
            name="Test Agent",
            gender=Gender.FEMALE,
            avatar="https://example.com/avatar.jpg",
            background="https://example.com/background.jpg",
            personality="温柔善良的女孩",
            scenario="在咖啡厅里与用户聊天",
            intro="一个可爱的AI助手",
            opening="你好！",
            visibility=AgentVisibility.PUBLIC,
            status=AgentStatus.APPROVED,
            creator_id=user_id,
        )
        db_session.add(test_agent)
        await db_session.commit()
        await db_session.refresh(test_agent)

        # 创建聊天会话（通过调用 get_or_create_chat_by_agent）
        chat = await chat_service.get_or_create_chat_by_agent(
            db=db_session, user_id=user_id, agent_id=agent_id
        )
        await db_session.refresh(chat)

        # 生成 session_id
        session_id = chat_service.generate_session_id(chat.id)

        # 创建聊天消息历史
        # 先创建一条用户消息
        user_message = models.ChatHistory(
            session_id=session_id,
            message={"type": "human", "data": {"content": "你好"}},
            meta_data={},
        )
        db_session.add(user_message)
        await db_session.flush()

        # 创建一条 AI 回复消息（这是要生成图片的消息）
        ai_message_content = "给我画一张你在咖啡厅的图片"
        ai_message = models.ChatHistory(
            session_id=session_id,
            message={"type": "ai", "data": {"content": ai_message_content}},
            meta_data={},
        )
        db_session.add(ai_message)
        await db_session.commit()
        await db_session.refresh(ai_message)
        message_id = ai_message.id

        # Mock 限额检查 - 允许生成
        mock_check_limit.return_value = (True, 2, 10)  # (is_allowed, used_count, daily_limit)

        # Mock 图片生成结果
        mock_image_result = {
            "message_id": message_id,
            "image_url": "https://cdn.example.com/test_image.jpg",
            "image_metadata": {
                "width": 1024,
                "height": 1024,
                "format": "jpeg",
            },
            "prompt": "构建的提示词...",
        }
        mock_generate_image.return_value = mock_image_result

        # Mock 用量记录
        mock_record_usage.return_value = None

        # 执行测试
        result = await chat_service.generate_chat_image(
            db=db_session,
            agent_id=agent_id,
            user_id=user_id,
            message_id=message_id,
            history_count=history_count,
        )

        # 验证结果
        assert isinstance(result, ChatImageGenerationResponse)
        assert result.model_dump() == mock_image_result
        assert result.message_id == message_id
        assert result.image_url == mock_image_result["image_url"]
        assert result.image_metadata == mock_image_result["image_metadata"]
        assert result.prompt == mock_image_result["prompt"]

        # 验证调用
        # 验证限额检查
        mock_check_limit.assert_called_once()
        check_limit_call_args = mock_check_limit.call_args
        assert check_limit_call_args[0][0] == db_session
        called_user = check_limit_call_args[0][1]
        assert called_user.id == user_id

        # 验证图片生成服务调用
        mock_generate_image.assert_called_once()
        generate_call_args = mock_generate_image.call_args
        assert generate_call_args[1]["db"] == db_session
        assert generate_call_args[1]["session_id"] == session_id
        assert generate_call_args[1]["message_id"] == message_id
        assert generate_call_args[1]["agent_data"]["id"] == agent_id
        assert generate_call_args[1]["message_content"] == ai_message_content
        assert generate_call_args[1]["history_count"] == history_count

        # 验证用量记录
        mock_record_usage.assert_called_once()
        record_call_args = mock_record_usage.call_args
        assert record_call_args[0][0] == db_session
        assert record_call_args[0][1] == user_id
        assert record_call_args[0][2] == "image_generation"
        assert record_call_args[0][3] == 1
        assert record_call_args[1]["extra_data"]["agent_id"] == agent_id
        assert record_call_args[1]["extra_data"]["message_content"] == ai_message_content[:100]

        # 清理测试数据（可选，因为测试数据库可能会自动清理）
        await db_session.delete(ai_message)
        await db_session.delete(user_message)
        await db_session.delete(chat)
        await db_session.delete(test_agent)
        await db_session.delete(test_user)
        await db_session.commit()

