# CREATED_BY_AGENT: cursor-gpt-5.2 (2025-12-21)

from types import SimpleNamespace
from unittest.mock import patch

from app.core.config import (
    GEMINI_2_5_FLASH,
    GEMINI_2_5_FLASH_LITE,
    AgentConfig,
    global_config_loaded_from_config_yaml,
)
from app.core.model_selection import (
    select_chat_image_model,
    select_chat_model,
    select_text_to_image_model,
)


def test_select_chat_model_free_user_uses_free_model():
    user = SimpleNamespace(is_superuser=False, email=None)
    model = select_chat_model(user=user, is_subscribed=False)
    assert model == GEMINI_2_5_FLASH_LITE


def test_select_chat_model_subscribed_user_uses_sub_model():
    user = SimpleNamespace(is_superuser=False, email=None)
    model = select_chat_model(user=user, is_subscribed=True)
    assert model == GEMINI_2_5_FLASH


def test_select_chat_model_superuser_by_is_superuser_field():
    user = SimpleNamespace(is_superuser=True, email=None)
    model = select_chat_model(user=user, is_subscribed=False)
    assert model == GEMINI_2_5_FLASH


def test_select_chat_model_superuser_by_email():
    user = SimpleNamespace(is_superuser=False, email="it@sxwl.ai")
    model = select_chat_model(user=user, is_subscribed=False)
    assert model == GEMINI_2_5_FLASH


def test_select_chat_model_superuser_by_email_case_insensitive():
    user = SimpleNamespace(is_superuser=False, email="IT@SXWL.AI")
    model = select_chat_model(user=user, is_subscribed=False)
    assert model == GEMINI_2_5_FLASH


def test_select_chat_model_falls_back_to_model_when_sub_user_chat_model_is_none():
    user = SimpleNamespace(is_superuser=False, email=None)
    mock_agent_config = AgentConfig(
        api_key="test",
        langchain_api_key="test",
        model="fallback-model",
        sub_user_chat_model=None,
        free_user_chat_model="free-model",
    )
    mock_config = SimpleNamespace(agent=mock_agent_config)
    with patch("app.core.model_selection.global_config_loaded_from_config_yaml", mock_config):
        model = select_chat_model(user=user, is_subscribed=True)
        assert model == "fallback-model"


def test_select_chat_model_falls_back_to_model_when_free_user_chat_model_is_none():
    user = SimpleNamespace(is_superuser=False, email=None)
    mock_agent_config = AgentConfig(
        api_key="test",
        langchain_api_key="test",
        model="fallback-model",
        sub_user_chat_model="sub-model",
        free_user_chat_model=None,
    )
    mock_config = SimpleNamespace(agent=mock_agent_config)
    with patch("app.core.model_selection.global_config_loaded_from_config_yaml", mock_config):
        model = select_chat_model(user=user, is_subscribed=False)
        assert model == "fallback-model"


def test_select_chat_model_works_with_partially_populated_user():
    user = SimpleNamespace()
    model = select_chat_model(user=user, is_subscribed=False)
    assert model == GEMINI_2_5_FLASH_LITE


def test_select_text_to_image_model_free_user():
    user = SimpleNamespace(is_superuser=False, email=None)
    model = select_text_to_image_model(user=user, is_subscribed=False)
    assert model == global_config_loaded_from_config_yaml.agent.free_user_text_to_image_model


def test_select_text_to_image_model_subscribed_user():
    user = SimpleNamespace(is_superuser=False, email=None)
    model = select_text_to_image_model(user=user, is_subscribed=True)
    assert model == global_config_loaded_from_config_yaml.agent.sub_user_text_to_image_model


def test_select_text_to_image_model_superuser_by_is_superuser_field():
    user = SimpleNamespace(is_superuser=True, email=None)
    model = select_text_to_image_model(user=user, is_subscribed=False)
    assert model == global_config_loaded_from_config_yaml.agent.sub_user_text_to_image_model


def test_select_text_to_image_model_superuser_by_email():
    user = SimpleNamespace(is_superuser=False, email="it@sxwl.ai")
    model = select_text_to_image_model(user=user, is_subscribed=False)
    assert model == global_config_loaded_from_config_yaml.agent.sub_user_text_to_image_model


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


def test_select_text_to_image_model_works_with_partially_populated_user():
    user = SimpleNamespace()
    model = select_text_to_image_model(user=user, is_subscribed=False)
    assert model == global_config_loaded_from_config_yaml.agent.free_user_text_to_image_model


def test_select_text_to_image_model_returns_vertex_when_config_is_fal_model():
    """Fal models are never returned; vertex_image_model is used instead."""
    user = SimpleNamespace(is_superuser=False, email=None)
    mock_agent_config = AgentConfig(
        api_key="test",
        langchain_api_key="test",
        vertex_image_model="imagen-4.0-fast-generate-001",
        sub_user_text_to_image_model="sub-image-model",
        free_user_text_to_image_model="fal-ai/z-image/turbo",
    )
    mock_config = SimpleNamespace(agent=mock_agent_config)
    with patch("app.core.model_selection.global_config_loaded_from_config_yaml", mock_config):
        model = select_text_to_image_model(user=user, is_subscribed=False)
        assert model == "imagen-4.0-fast-generate-001"


def test_select_chat_image_model_returns_gemini_when_config_is_fal_model():
    """Fal models are never returned; 'gemini' is used instead."""
    user = SimpleNamespace(is_superuser=False, email=None)
    mock_agent_config = AgentConfig(
        api_key="test",
        langchain_api_key="test",
        sub_user_chat_image_model="gemini",
        free_user_chat_image_model="fal-ai/z-image/turbo/image-to-image",
    )
    mock_config = SimpleNamespace(agent=mock_agent_config)
    with patch("app.core.model_selection.global_config_loaded_from_config_yaml", mock_config):
        model = select_chat_image_model(user=user, is_subscribed=False)
        assert model == "gemini"
