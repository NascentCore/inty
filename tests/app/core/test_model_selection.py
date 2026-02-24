# CREATED_BY_AGENT: cursor-gpt-5.2 (2025-12-21)

from types import SimpleNamespace
from unittest.mock import patch

from app.core.config import (
    GEMINI_2_5_FLASH,
    GEMINI_2_5_FLASH_LITE,
    AgentConfig,
    global_config_loaded_from_config_yaml as global_config,
)
from app.core.model_selection import select_chat_model, select_text_to_image_model


def test_select_chat_model_free_user_uses_free_model():
    user = SimpleNamespace(is_superuser=False, email=None)
    model = select_chat_model(user=user, is_subscribed=False)
    assert model == global_config.agent.free_user_chat_model


def test_select_chat_model_subscribed_user_uses_sub_model():
    user = SimpleNamespace(is_superuser=False, email=None)
    model = select_chat_model(user=user, is_subscribed=True)
    assert model == global_config.agent.sub_user_chat_model


def test_select_text_to_image_model_free_user():
    user = SimpleNamespace(is_superuser=False, email=None)
    model = select_text_to_image_model(user=user, is_subscribed=False)
    assert model == global_config.agent.free_user_text_to_image_model


def test_select_text_to_image_model_subscribed_user():
    user = SimpleNamespace(is_superuser=False, email=None)
    model = select_text_to_image_model(user=user, is_subscribed=True)
    assert model == global_config.agent.sub_user_text_to_image_model


def test_select_text_to_image_model_falls_back_to_vertex_image_model_when_sub_user_model_is_none():
    user = SimpleNamespace(is_superuser=False, email=None)
    mock_agent_config = AgentConfig(
        api_key="test",
        langchain_api_key="test",
        vertex_image_model="fallback-vertex-model",
        sub_user_text_to_image_model=None,
        free_user_text_to_image_model="free-image-model",
    )
    mock_config = SimpleNamespace(agent=mock_agent_config)
    with patch("app.core.model_selection.global_config_loaded_from_config_yaml", mock_config):
        model = select_text_to_image_model(user=user, is_subscribed=True)
        assert model == "fallback-vertex-model"


def test_select_text_to_image_model_falls_back_to_vertex_image_model_when_free_user_model_is_none():
    user = SimpleNamespace(is_superuser=False, email=None)
    mock_agent_config = AgentConfig(
        api_key="test",
        langchain_api_key="test",
        vertex_image_model="fallback-vertex-model",
        sub_user_text_to_image_model="sub-image-model",
        free_user_text_to_image_model=None,
    )
    mock_config = SimpleNamespace(agent=mock_agent_config)
    with patch("app.core.model_selection.global_config_loaded_from_config_yaml", mock_config):
        model = select_text_to_image_model(user=user, is_subscribed=False)
        assert model == "fallback-vertex-model"
