"""
image_generation_service 模块级函数单元测试（如 _serialize_gemini_response_for_log）
及生图失败时日志记录验证（FakeGeminiClient 模拟失效）。
build_image_prompt 单元测试验证提示词拼接与 fallback 逻辑。
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.external_services.fakes.gemini import FakeGeminiClient
from app.services.image_generation_service import (
    _serialize_gemini_response_for_log,
    image_generation_service,
)


class TestBuildImagePrompt:
    """build_image_prompt 构建生图提示词：agent 字段、历史格式化、模板占位符替换。"""

    def test_empty_inputs_returns_template_with_empty_placeholders(self):
        """空 agent、空历史、空消息、空 user_info 时，返回的提示词中对应位置为空。"""
        agent_data = {}
        chat_history = []
        user_message = ""
        user_info = ""

        result = image_generation_service.build_image_prompt(
            agent_data=agent_data,
            chat_history=chat_history,
            user_message=user_message,
            user_info=user_info,
        )

        assert isinstance(result, str)
        assert "Recent dialogue:" in result
        assert "User request:" in result

    def test_agent_scenario_and_personality_appear_in_prompt(self):
        """agent_data 的 scenario、personality 应出现在最终提示词中。"""
        agent_data = {
            "scenario": "Coffee shop in Paris",
            "personality": "Warm and witty",
        }
        chat_history = []
        user_message = "Draw us at the table"
        user_info = ""

        result = image_generation_service.build_image_prompt(
            agent_data=agent_data,
            chat_history=chat_history,
            user_message=user_message,
            user_info=user_info,
        )

        assert "Coffee shop in Paris" in result
        assert "Warm and witty" in result
        assert "Draw us at the table" in result

    def test_agent_uses_intro_when_scenario_missing(self):
        """当 agent 无 scenario 时，使用 intro 作为背景。"""
        agent_data = {
            "personality": "Friendly",
            "intro": "She works at a bookstore",
        }
        chat_history = []
        user_message = "Hi"
        user_info = ""

        result = image_generation_service.build_image_prompt(
            agent_data=agent_data,
            chat_history=chat_history,
            user_message=user_message,
            user_info=user_info,
        )

        assert "She works at a bookstore" in result
        assert "Friendly" in result

    def test_chat_history_formatted_as_user_and_ai_lines(self):
        """聊天历史格式化为「用户: ...」「AI: ...」多行。"""
        agent_data = {"scenario": "", "personality": ""}
        chat_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "Draw a sunset"},
        ]
        user_message = "with me in it"
        user_info = ""

        result = image_generation_service.build_image_prompt(
            agent_data=agent_data,
            chat_history=chat_history,
            user_message=user_message,
            user_info=user_info,
        )

        assert "用户: Hello" in result
        assert "AI: Hi there!" in result
        assert "用户: Draw a sunset" in result
        assert "with me in it" in result

    def test_chat_history_ignores_unknown_roles(self):
        """仅 role 为 user / assistant 的消息参与拼接，其他 role 不出现。"""
        agent_data = {}
        chat_history = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Only user"},
        ]
        user_message = "msg"
        user_info = ""

        result = image_generation_service.build_image_prompt(
            agent_data=agent_data,
            chat_history=chat_history,
            user_message=user_message,
            user_info=user_info,
        )

        assert "用户: Only user" in result
        assert "System prompt" not in result
        assert "msg" in result

    def test_chat_history_missing_role_or_content_uses_empty(self):
        """历史消息缺少 role/content 时用空字符串，不抛错。"""
        agent_data = {}
        chat_history = [
            {"role": "user"},
            {"content": "no role"},
            {"role": "assistant", "content": "reply"},
        ]
        user_message = "x"
        user_info = ""

        result = image_generation_service.build_image_prompt(
            agent_data=agent_data,
            chat_history=chat_history,
            user_message=user_message,
            user_info=user_info,
        )

        assert "用户: " in result
        assert "AI: reply" in result
        assert "x" in result

    def test_user_info_appears_in_prompt(self):
        """user_info 非空时完整出现在提示词中。"""
        agent_data = {}
        chat_history = []
        user_message = "draw"
        user_info = "## User Information\nAge: 30, Location: NYC"

        result = image_generation_service.build_image_prompt(
            agent_data=agent_data,
            chat_history=chat_history,
            user_message=user_message,
            user_info=user_info,
        )

        assert "## User Information" in result
        assert "Age: 30" in result
        assert "NYC" in result
        assert "draw" in result

    def test_default_user_info_is_empty_string(self):
        """不传 user_info 时默认为空字符串，模板中对应位置为空。"""
        agent_data = {"scenario": "S", "personality": "P"}
        chat_history = []
        user_message = "m"

        result = image_generation_service.build_image_prompt(
            agent_data=agent_data,
            chat_history=chat_history,
            user_message=user_message,
        )

        assert "S" in result
        assert "P" in result
        assert "m" in result


class TestSerializeGeminiResponseForLog:
    """_serialize_gemini_response_for_log 防御性序列化"""

    def test_returns_empty_dict_when_response_is_none(self):
        assert _serialize_gemini_response_for_log(None) == {}

    def test_candidate_content_parts_none_does_not_raise(self):
        """c.content.parts 为 None 时不抛错，该 candidate 不包含 content_parts 或 content 为 None"""
        c = Mock()
        c.finish_reason = None
        c.safety_ratings = None
        c.content = Mock()
        c.content.parts = None  # 会触发 'NoneType' object is not iterable 的根因
        response = Mock()
        response.prompt_feedback = None
        response.candidates = [c]

        result = _serialize_gemini_response_for_log(response)

        assert "candidates" in result
        assert len(result["candidates"]) == 1
        entry = result["candidates"][0]
        assert "content_parts" not in entry
        assert entry.get("content") is None

    def test_candidate_safety_ratings_none_does_not_raise(self):
        """c.safety_ratings 为 None 时不抛错"""
        c = Mock()
        c.finish_reason = None
        c.safety_ratings = None  # 属性存在但为 None
        c.content = None
        response = Mock()
        response.prompt_feedback = None
        response.candidates = [c]

        result = _serialize_gemini_response_for_log(response)

        assert result["candidates"][0].get("safety_ratings") is None

    def test_candidate_content_none_with_parts_attribute_does_not_raise(self):
        """c.content 为 None 时即使 hasattr(c.content, 'parts') 不触发，迭代安全"""
        c = Mock()
        c.finish_reason = None
        c.safety_ratings = []
        c.content = None
        response = Mock()
        response.prompt_feedback = None
        response.candidates = [c]

        result = _serialize_gemini_response_for_log(response)

        assert len(result["candidates"]) == 1
        assert result["candidates"][0].get("content") is None


class TestGenerateChatImageFailureLogging:
    """生图失败时验证 _log_image_generation_failure 记录完整提示词与失败原因。"""

    @pytest.mark.asyncio
    @patch("app.services.image_generation_service.chat_history_service.get_messages_paginated")
    @patch("app.services.image_generation_service.get_genai_client")
    async def test_fake_gemini_failure_logs_prompt_and_response(
        self,
        mock_get_client: Mock,
        mock_get_messages: Mock,
    ):
        """FakeGeminiClient 模拟 generate_content 返回空 candidates，在测试中看到「生图失败 - 完整提示词:」的日志条目。"""
        mock_get_client.return_value = FakeGeminiClient(fail_generate_content=True)
        mock_get_messages.return_value = {
            "messages": [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "你好呀"},
            ],
            "total": 2,
        }

        mock_db = AsyncMock(spec=AsyncSession)
        agent_data = {
            "id": "agent_1",
            "personality": "温柔",
            "scenario": "在咖啡厅",
            "background": "https://example.com/bg.jpg",
        }
        message_content = "画一张在咖啡厅的图"
        expected_log_prefix = "生图失败 - 完整提示词:"
        expected_prompt_fragment = "咖啡厅"

        captured: list[str] = []

        def sink(message):
            captured.append(message.record["message"])

        handler_id = logger.add(sink, level="ERROR")
        try:
            with pytest.raises(ValueError, match="Gemini returned no candidates"):
                await image_generation_service.generate_chat_image_with_gemini(
                    db=mock_db,
                    session_id="test_session",
                    message_id=1,
                    agent_data=agent_data,
                    message_content=message_content,
                    user_id=None,
                    history_count=5,
                )
        finally:
            logger.remove(handler_id)

        # 用户输入提示词应出现在某条捕获的日志内
        assert any(
            message_content in m for m in captured
        ), (
            f"期望捕获的日志内包含用户输入提示词 {message_content!r}, 实际: {captured!r}"
        )

        prompt_lines = [m for m in captured if expected_log_prefix in m]
        assert prompt_lines, (
            f"期望看到包含 {expected_log_prefix!r} 的日志条目，实际捕获的 ERROR 日志: {captured!r}"
        )
        assert any(
            expected_prompt_fragment in line for line in prompt_lines
        ), (
            f"期望该日志条目包含提示词片段 {expected_prompt_fragment!r}, "
            f"实际: {prompt_lines!r}"
        )

        # 应还有「生图失败 - Gemini 返回:」的一行，且该行包含序列化后的 Gemini 返回（如 candidates）
        gemini_lines = [m for m in captured if "生图失败 - Gemini 返回:" in m]
        assert len(gemini_lines) >= 1, (
            f"期望看到「生图失败 - Gemini 返回:」的日志条目，实际: {captured!r}"
        )
        expected_gemini_fragment = "candidates"  # 空 candidates 时序列化为 {"candidates": []}
        assert any(
            expected_gemini_fragment in line for line in gemini_lines
        ), (
            f"期望 Gemini 返回日志行包含序列化内容（如 {expected_gemini_fragment!r}），实际: {gemini_lines!r}"
        )
