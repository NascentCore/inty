# CREATED_BY_AGENT
"""节日记忆服务单元测试"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from app.services import festival_memory_service
from app.services.memory_service import get_festival_memories_for_user_agent


class TestGetFestivalMemoriesForUserAgent:
    """get_festival_memories_for_user_agent 返回格式与空结果"""

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_memories(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        out = await get_festival_memories_for_user_agent(mock_db, "user-1", "agent-1")
        assert out == []

    @pytest.mark.asyncio
    async def test_returns_list_with_festival_date_name_memory(self):
        mock_db = AsyncMock()
        mock_row = (42, date(2026, 2, 10), "春节", "用户与角色在春节相关的回忆摘要")
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        mock_db.execute = AsyncMock(return_value=mock_result)
        out = await get_festival_memories_for_user_agent(mock_db, "user-1", "agent-1")
        assert len(out) == 1
        assert out[0]["memory_id"] == 42
        assert out[0]["festival_date"] == "2026-02-10"
        assert out[0]["festival_name"] == "春节"
        assert out[0]["memory"] == "用户与角色在春节相关的回忆摘要"


class TestAssembleArgs:
    """assemble_args 返回 (full_prompt, LLMConfig)，有无 llm_config 时 model/temperature/max_tokens 来自 LLMConfig"""

    def test_with_llm_config_uses_custom_model_and_params(self):
        messages = [("user", "hi"), ("assistant", "hello")]
        llm_config = {
            "model": "anthropic/claude-3.5-sonnet",
            "temperature": 0.5,
            "max_tokens": 4096,
        }
        full_prompt, ext_llm_config = festival_memory_service.assemble_args(
            messages,
            "春节",
            date(2026, 2, 1),
            "Extract memories.",
            llm_config=llm_config,
        )
        assert "春节" in full_prompt and "Extract memories." in full_prompt
        assert ext_llm_config.model == "anthropic/claude-3.5-sonnet"
        assert ext_llm_config.max_tokens == 4096
        assert ext_llm_config.temperature == 0.5

    def test_with_invalid_temperature_or_max_tokens_raises_validation_error(self):
        """非法 numeric 的 dict 经 model_validate 会抛出 ValidationError。"""
        messages = [("user", "hi")]
        llm_config = {
            "model": "some/model",
            "temperature": "not-a-number",
            "max_tokens": "invalid",
        }
        with pytest.raises(ValidationError):
            festival_memory_service.assemble_args(
                messages,
                "春节",
                date(2026, 2, 1),
                "Prompt.",
                llm_config=llm_config,
            )

    def test_with_empty_model_in_config_falls_back_to_default(self):
        messages = [("user", "hi")]
        llm_config = {"model": "", "temperature": 0.8}
        with patch.object(
            festival_memory_service,
            "global_config_loaded_from_config_yaml",
            MagicMock(memory_extraction=MagicMock(model=None)),
        ):
            full_prompt, ext_llm_config = festival_memory_service.assemble_args(
                messages,
                "春节",
                date(2026, 2, 1),
                "Prompt.",
                llm_config=llm_config,
            )
        assert (
            ext_llm_config.model
            == festival_memory_service.DEFAULT_FESTIVAL_EXTRACTION_MODEL
        )
        assert ext_llm_config.max_tokens == 2000
        assert ext_llm_config.temperature == 0.0

    def test_without_llm_config_uses_default(self):
        messages = [("user", "hi")]
        with patch.object(
            festival_memory_service,
            "global_config_loaded_from_config_yaml",
            MagicMock(memory_extraction=MagicMock(model=None)),
        ):
            full_prompt, ext_llm_config = festival_memory_service.assemble_args(
                messages, "春节", date(2026, 2, 1), "Prompt."
            )
        assert (
            ext_llm_config.model
            == festival_memory_service.DEFAULT_FESTIVAL_EXTRACTION_MODEL
        )
        assert ext_llm_config.max_tokens == 2000
        assert ext_llm_config.temperature == 0.0
