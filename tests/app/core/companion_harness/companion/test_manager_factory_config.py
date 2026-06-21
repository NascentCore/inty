"""Tests for companion_config_for_resolved_model factory helper."""

from __future__ import annotations

from app.core.companion_harness.companion.manager_factory import (
    companion_config_for_resolved_model,
    companion_tool_model_api_id,
)
from app.utils.models_catalog import DEEPSEEK_V3_2, resolve_chat_text_model


def test_companion_config_for_resolved_model_honors_distinct_tool_model() -> (
    None
):
    chat_m = DEEPSEEK_V3_2
    tool_api_id = companion_tool_model_api_id(chat_m.id_on_provider)
    tool_m = resolve_chat_text_model(tool_api_id)
    cfg = companion_config_for_resolved_model(chat_m, tool_m)
    assert cfg.llm.chat_model == chat_m
    assert cfg.llm.tool_model == tool_m
