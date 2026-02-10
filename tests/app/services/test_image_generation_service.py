"""
image_generation_service 模块级函数单元测试（如 _serialize_gemini_response_for_log）
"""

from unittest.mock import Mock

import pytest

from app.services.image_generation_service import (
    _serialize_gemini_response_for_log,
)


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
