"""
聊天生图功能集成测试 - 使用 Gemini 2.5 Flash Image
"""

import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.core.config import global_config_loaded_from_config_yaml
from app.external_services.fakes.gemini import FakeGeminiClient
from app.models.agent import AgentStatus, AgentVisibility
from app.models.user import AuthType, Gender
from app.services import chat_history_service
from app.services.image_generation_service import image_generation_service


@pytest.fixture
async def db_session():
    engine = create_async_engine(
        str(global_config_loaded_from_config_yaml.database.async_url),
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=True,
    )
    async_session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


class TestImageGenerationService:
    """测试图片生成服务"""

    @pytest.mark.asyncio
    async def test_build_image_prompt(self):
        """测试提示词构建"""
        agent_data = {
            "personality": "温柔善良的女孩",
            "scenario": "在咖啡厅里与用户聊天",
            "intro": "一个可爱的AI助手",
        }

        chat_history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好呀！"},
            {"role": "user", "content": "今天天气真好"},
        ]

        user_message = "给我画一张你在咖啡厅的图片"

        prompt = image_generation_service.build_image_prompt(
            agent_data=agent_data,
            chat_history=chat_history,
            user_message=user_message,
        )

        # 验证提示词包含所有必要信息
        assert "温柔善良的女孩" in prompt
        assert "在咖啡厅里与用户聊天" in prompt
        assert "你好" in prompt
        assert "今天天气真好" in prompt
        assert "给我画一张你在咖啡厅的图片" in prompt

    @pytest.mark.asyncio
    async def test_build_image_prompt_with_user_info(self):
        """测试提示词构建（包含用户信息）"""
        agent_data = {
            "personality": "温柔善良的女孩",
            "scenario": "在咖啡厅里与用户聊天",
        }

        chat_history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好呀！"},
        ]

        user_message = "给我画一张图片"
        user_info = "##User Information\nName: TestUser\nGender: Male\nAge: 25-30"

        prompt = image_generation_service.build_image_prompt(
            agent_data=agent_data,
            chat_history=chat_history,
            user_message=user_message,
            user_info=user_info,
        )

        # 验证提示词包含用户信息
        assert "##User Information" in prompt
        assert "Name: TestUser" in prompt
        assert "Gender: Male" in prompt
        assert "Age: 25-30" in prompt

    @pytest.mark.asyncio
    @patch("app.services.image_generation_service.agent_service.append_agent_background_image")
    @patch("app.services.image_generation_service.image_transform_service")
    @patch("app.services.image_generation_service.get_genai_client")
    @patch("app.core.google_genai.wrapped_client.upload_to_gcs")
    @patch("app.services.chat_history_service.get_messages_paginated")
    @patch("app.services.chat_history_service.update_message_metadata")
    @patch("app.services.image_generation_service.PIL.Image")
    async def test_generate_chat_image_with_gemini(
        self,
        mock_pil_image: Mock,
        mock_update_metadata: AsyncMock,
        mock_get_messages: Mock,
        mock_upload_gcs: Mock,
        mock_get_client: Mock,
        mock_transform_service: Mock,
        mock_append_background: AsyncMock,
    ):
        """测试使用 Gemini 生成聊天图片"""
        # 准备测试数据
        mock_db = AsyncMock(spec=AsyncSession)
        session_id = "test_session_123"
        message_id = 12345
        agent_data = {
            "id": "agent_123",
            "personality": "可爱的女孩",
            "scenario": "在公园散步",
            "background": "https://example.com/background.jpg",
        }
        message_content = "给我画一张图片"

        # Mock 聊天历史
        mock_get_messages.return_value = {
            "messages": [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "你好呀"},
            ],
            "total": 2,
        }

        # Mock Gemini 客户端响应
        import base64

        # 创建一个简单的测试图片数据
        test_image_data = b"fake_image_data_1234567890"
        encoded_image = base64.b64encode(test_image_data).decode()

        # Mock inline_data
        mock_inline_data = Mock()
        mock_inline_data.data = encoded_image

        # Mock part
        mock_part = Mock()
        mock_part.inline_data = mock_inline_data

        # Mock content
        mock_content = Mock()
        mock_content.parts = [mock_part]

        # Mock candidate
        mock_candidate = Mock()
        mock_candidate.content = mock_content
        mock_candidate.finish_reason = None
        mock_candidate.safety_ratings = []

        # Mock response
        mock_response = Mock()
        mock_response.candidates = [mock_candidate]
        mock_response.prompt_feedback = None

        # Mock client - WrappedClient 使用 client.aio.models.generate_content（异步）
        mock_client_instance = Mock()
        mock_client_instance.aio = Mock()
        mock_client_instance.aio.models = Mock()
        mock_client_instance.aio.models.generate_content = AsyncMock(
            return_value=mock_response
        )
        mock_get_client.return_value = mock_client_instance

        # GCS upload 在 WrappedClient._process_image_part_to_generated_image 内调用，由上面的 patch 注入
        mock_upload_gcs.return_value = None

        # Mock PIL Image
        mock_image_instance = Mock()
        mock_image_instance.size = (1024, 1792)
        mock_image_instance.format = "JPEG"
        mock_pil_image.open.return_value = mock_image_instance

        # Mock CDN URL 转换
        mock_transform_service.transform_desktop.return_value = "https://cdn.example.com/test_image.jpg"

        # Mock 消息元数据更新
        mock_update_metadata.return_value = True

        # 执行测试
        result = await image_generation_service.generate_chat_image_with_gemini(
            db=mock_db,
            session_id=session_id,
            message_id=message_id,
            agent_data=agent_data,
            message_content=message_content,
            history_count=10,
        )

        # 验证结果
        assert "image_url" in result
        assert "image_metadata" in result
        assert "prompt" in result
        assert "message_id" in result
        assert result["message_id"] == 12345

        # 验证调用
        mock_get_messages.assert_called_once()
        mock_get_client.assert_called_once()
        mock_upload_gcs.assert_called_once()
        mock_update_metadata.assert_called_once()
        mock_append_background.assert_awaited_once()


class TestChatHistoryService:
    """测试聊天历史服务"""

    @pytest.mark.asyncio
    async def test_add_ai_image_message(self):
        """测试添加AI图片消息"""
        mock_db = AsyncMock(spec=AsyncSession)
        session_id = "test_session_123"
        image_url = "gs://bucket/image.jpg"
        image_metadata = {
            "width": 1024,
            "height": 1792,
            "format": "jpeg",
        }
        prompt = "测试提示词"
        agent_id = "agent_123"

        # Mock ChatHistory 对象
        from app.models.chat_history import ChatHistory

        mock_chat_history = Mock(spec=ChatHistory)
        mock_chat_history.id = 12345

        # Mock db.add 和 commit
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # 设置 refresh 的副作用
        async def set_id(obj):
            obj.id = 12345

        mock_db.refresh.side_effect = set_id

        # 由于实际测试需要真实的数据库连接，这里只是一个框架
        # 实际测试应该使用测试数据库
        pass

    @pytest.mark.asyncio
    async def test_generate_chat_image_appends_agent_background_images(
        self,
        monkeypatch: pytest.MonkeyPatch,
        db_session: AsyncSession,
    ):
        """生成聊天图片后应将GCS图片追加到Agent的background_images"""
        mock_update_metadata = AsyncMock(return_value=True)
        monkeypatch.setattr(
            chat_history_service,
            "update_message_metadata",
            mock_update_metadata,
        )
        monkeypatch.setattr(
            chat_history_service,
            "get_messages_paginated",
            lambda *args, **kwargs: {"messages": [], "total": 0},
        )
        monkeypatch.setattr(
            "app.services.image_generation_service.get_genai_client",
            lambda: FakeGeminiClient(),
        )

        def fake_upload(file_data, content_type, bucket_name, path):
            return f"https://storage.googleapis.com/{bucket_name}/{path}"

        monkeypatch.setattr(
            "app.services.image_generation_service.upload_to_gcs",
            fake_upload,
        )
        monkeypatch.setattr(
            "app.services.image_generation_service.image_transform_service.transform_desktop",
            lambda url: f"https://cdn.example.com/{url.split('/', 3)[-1]}",
        )

        session = db_session
        user_id = f"user-{uuid.uuid4().hex[:8]}"
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"

        user = models.User(
            id=user_id,
            readable_id=uuid.uuid4().hex[:8],
            auth_type=AuthType.PHONE,
            nickname="Chat Tester",
            email="test@example.com",
            system_language="en",
        )
        session.add(user)
        await session.commit()

        agent = models.Agent(
            id=agent_id,
            readable_id=uuid.uuid4().hex[:8],
            name="Chat Image Agent",
            gender=Gender.FEMALE,
            avatar="https://storage.googleapis.com/test-bucket/avatar.jpg",
            background="https://storage.googleapis.com/test-bucket/background.jpg",
            personality="gentle",
            scenario="coffee shop",
            intro="intro text",
            opening="hello",
            visibility=AgentVisibility.PUBLIC,
            status=AgentStatus.APPROVED,
            creator_id=user_id,
            background_images=["gs://test-bucket/original.jpg"],
        )
        session.add(agent)
        await session.commit()
        await session.refresh(agent)

        agent_data = {
            "id": agent_id,
            "personality": agent.personality,
            "scenario": agent.scenario,
            "intro": agent.intro,
            "background": agent.background,
        }

        session_id = "session-test"
        message_id = 1001

        result = await image_generation_service.generate_chat_image_with_gemini(
            db=session,
            session_id=session_id,
            message_id=message_id,
            agent_data=agent_data,
            message_content="please draw an image",
            history_count=5,
        )

        assert result["message_id"] == message_id
        assert result["image_url"].startswith("https://cdn.example.com/")
        mock_update_metadata.assert_awaited()

        await session.refresh(agent)
        assert agent.background_images[0] == "gs://test-bucket/original.jpg"
        assert len(agent.background_images) == 2
        bucket = global_config_loaded_from_config_yaml.gcs.bucket
        assert agent.background_images[1].startswith(f"gs://{bucket}/chat_images/")

        await session.delete(agent)
        await session.delete(user)
        await session.commit()

    @pytest.mark.asyncio
    async def test_generate_chat_image_with_gemini_writes_db_records_as_expected(
        self,
        monkeypatch: pytest.MonkeyPatch,
        db_session: AsyncSession,
    ):
        """generate_chat_image_with_gemini 写入的 DB 记录符合预期：消息 meta_data、Agent background_images、Resource 表。"""
        monkeypatch.setattr(
            chat_history_service,
            "get_messages_paginated",
            lambda *args, **kwargs: {"messages": [], "total": 0},
        )
        monkeypatch.setattr(
            "app.services.image_generation_service.get_genai_client",
            lambda: FakeGeminiClient(),
        )

        def fake_upload(file_data, content_type, bucket_name, path):
            return "https://storage.googleapis.com/{}/{}".format(bucket_name, path)

        monkeypatch.setattr(
            "app.core.google_genai.wrapped_client.upload_to_gcs",
            fake_upload,
        )
        monkeypatch.setattr(
            "app.services.image_generation_service.image_transform_service.transform_desktop",
            lambda url: "https://cdn.example.com/{}".format(url.split("/", 3)[-1]),
        )

        session = db_session
        user_id = "user-{}".format(uuid.uuid4().hex[:8])
        agent_id = "agent-{}".format(uuid.uuid4().hex[:8])
        session_uuid = uuid.uuid4()
        session_id_str = str(session_uuid)

        user = models.User(
            id=user_id,
            readable_id=uuid.uuid4().hex[:8],
            auth_type=AuthType.PHONE,
            nickname="Chat Tester",
            email="test@example.com",
            system_language="en",
        )
        session.add(user)
        await session.commit()

        agent = models.Agent(
            id=agent_id,
            readable_id=uuid.uuid4().hex[:8],
            name="Chat Image Agent",
            gender=Gender.FEMALE,
            avatar="https://storage.googleapis.com/test-bucket/avatar.jpg",
            background="https://storage.googleapis.com/test-bucket/background.jpg",
            personality="gentle",
            scenario="coffee shop",
            intro="intro text",
            opening="hello",
            visibility=AgentVisibility.PUBLIC,
            status=AgentStatus.APPROVED,
            creator_id=user_id,
            background_images=["gs://test-bucket/original.jpg"],
        )
        session.add(agent)
        await session.commit()
        await session.refresh(agent)

        # 真实消息行，以便 update_message_metadata 能更新
        chat_msg = models.ChatHistory(
            session_id=session_uuid,
            message={"type": "user", "data": {"content": "draw an image"}},
            meta_data=None,
        )
        session.add(chat_msg)
        await session.commit()
        await session.refresh(chat_msg)
        message_id = chat_msg.id

        agent_data = {
            "id": agent_id,
            "personality": agent.personality,
            "scenario": agent.scenario,
            "intro": agent.intro,
            "background": agent.background,
        }

        result = await image_generation_service.generate_chat_image_with_gemini(
            db=session,
            session_id=session_id_str,
            message_id=message_id,
            agent_data=agent_data,
            message_content="please draw an image",
            user_id=user_id,
            history_count=5,
        )

        assert result["message_id"] == message_id
        assert result["image_url"].startswith("https://cdn.example.com/")

        # 1) 消息 meta_data 中应有 generated_image
        stmt = select(models.ChatHistory).where(
            models.ChatHistory.session_id == session_uuid,
            models.ChatHistory.id == message_id,
        )
        row = (await session.execute(stmt)).scalar_one_or_none()
        assert row is not None
        assert row.meta_data is not None
        gen = row.meta_data.get("generated_image")
        assert gen is not None
        assert "image_url" in gen
        assert gen["image_url"].startswith("gs://")
        assert gen.get("width") is not None
        assert gen.get("height") is not None
        assert gen.get("format") is not None
        assert gen.get("prompt") is not None
        assert gen.get("generated_at") is not None

        gcs_uri = gen["image_url"]

        # 2) Agent background_images 应包含新图
        await session.refresh(agent)
        assert len(agent.background_images) == 2
        assert agent.background_images[0] == "gs://test-bucket/original.jpg"
        assert gcs_uri in agent.background_images or agent.background_images[1] == gcs_uri

        # 3) Resource 表应有对应记录（user_id 传入时）
        res_stmt = select(models.Resource).where(models.Resource.url == gcs_uri)
        resource = (await session.execute(res_stmt)).scalar_one_or_none()
        assert resource is not None
        assert resource.agent_id == agent_id
        assert resource.user_id == user_id
        meta = resource.resource_metadata or {}
        assert meta.get("generation_prompt") is not None
        assert meta.get("gcs_url") == gcs_uri

        await session.delete(resource)
        await session.delete(chat_msg)
        await session.delete(agent)
        await session.delete(user)
        await session.commit()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
