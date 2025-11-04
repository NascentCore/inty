"""
聊天生图功能集成测试 - 使用 Gemini 2.5 Flash Image
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import chat_history_service
from app.services.image_generation_service import image_generation_service


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
    @patch("app.services.image_generation_service.image_transform_service")
    @patch("app.services.image_generation_service.get_genai_client")
    @patch("app.services.image_generation_service.upload_to_gcs")
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

        # Mock client - get_genai_client 返回一个配置好的客户端实例
        mock_client_instance = Mock()
        mock_client_instance.models.generate_content.return_value = mock_response
        mock_get_client.return_value = mock_client_instance

        # Mock GCS upload
        mock_upload_gcs.return_value = "https://storage.googleapis.com/bucket/chat_images/test_image.jpg"

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
