# CREATED_BY_AGENT: cursor-gpt-5.2 (2025-12-21)

from types import SimpleNamespace
from unittest.mock import patch

from app.core.config import (
    GEMINI_2_5_FLASH,
    GEMINI_2_5_FLASH_LITE,
    AgentConfig,
    global_config_loaded_from_config_yaml as global_config,
)
from app.core.model_selection import (
    select_chat_image_model,
    select_chat_model,
    select_chat_tts_model,
    select_text_to_image_model,
)
from app.utils.models_catalog import (
    DEEPSEEK_V3_2,
    NANO_BANANA,
    NANO_BANANA_PRO,
    SEEDREAM_V4_5_EDIT,
    Z_IMAGE_TURBO_IMAGE_TO_IMAGE,
)


def test_select_chat_model_free_user_uses_free_model():
    user = SimpleNamespace(is_superuser=False, email=None)
    model = select_chat_model(user=user, is_subscribed=False)
    assert model == global_config.agent.free_user_chat_model


def test_select_chat_model_subscribed_user_uses_sub_model():
    user = SimpleNamespace(is_superuser=False, email=None)
    model = select_chat_model(user=user, is_subscribed=True)
    assert model == global_config.agent.sub_user_chat_model


def test_select_chat_model_resolves_nickname_to_id():
    """Config 使用 nickname（如 DeepSeek V3.2）时，返回 id_on_provider 供 API 调用。"""
    user = SimpleNamespace()
    mock_agent = SimpleNamespace(
        free_user_chat_model=DEEPSEEK_V3_2.nickname,
        sub_user_chat_model=GEMINI_2_5_FLASH,
    )
    mock_config = SimpleNamespace(agent=mock_agent)
    with patch(
        "app.core.model_selection.global_config_loaded_from_config_yaml", mock_config
    ):
        model_free = select_chat_model(user=user, is_subscribed=False)
        assert model_free == DEEPSEEK_V3_2.id_on_provider
        model_sub = select_chat_model(user=user, is_subscribed=True)
        assert model_sub == GEMINI_2_5_FLASH


def test_select_chat_tts_model_free_user_uses_free_model():
    user = SimpleNamespace(is_superuser=False, email=None)
    model = select_chat_tts_model(user=user, is_subscribed=False)
    assert model == global_config.agent.free_user_chat_tts_model


def test_select_chat_tts_model_subscribed_user_uses_sub_model():
    user = SimpleNamespace(is_superuser=False, email=None)
    mock_agent = SimpleNamespace(
        free_user_chat_tts_model="gemini-2.5-flash-tts",
        sub_user_chat_tts_model="gemini-2.5-pro-tts",
    )
    mock_config = SimpleNamespace(agent=mock_agent)
    with patch(
        "app.core.model_selection.global_config_loaded_from_config_yaml", mock_config
    ):
        model = select_chat_tts_model(user=user, is_subscribed=True)
        assert model == "gemini-2.5-pro-tts"


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
    with patch(
        "app.core.model_selection.global_config_loaded_from_config_yaml", mock_config
    ):
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
    with patch(
        "app.core.model_selection.global_config_loaded_from_config_yaml", mock_config
    ):
        model = select_text_to_image_model(user=user, is_subscribed=False)
        assert model == "fallback-vertex-model"


def test_select_chat_image_model_returns_gen_ai_model():
    """select_chat_image_model 按订阅状态读 config nickname，返回 GenAIModel。"""
    user = SimpleNamespace()
    mock_agent = SimpleNamespace(
        free_user_chat_image_model=NANO_BANANA.nickname,
        sub_user_chat_image_model=NANO_BANANA_PRO.nickname,
    )
    mock_config = SimpleNamespace(agent=mock_agent)
    with patch(
        "app.core.model_selection.global_config_loaded_from_config_yaml", mock_config
    ):
        model_free = select_chat_image_model(user=user, is_subscribed=False)
        assert model_free is NANO_BANANA
        model_sub = select_chat_image_model(user=user, is_subscribed=True)
        assert model_sub is NANO_BANANA_PRO


def test_select_chat_image_model_uses_fal_nickname():
    """select_chat_image_model 支持 fal 模型 nickname。"""
    user = SimpleNamespace()
    mock_agent = SimpleNamespace(
        free_user_chat_image_model=Z_IMAGE_TURBO_IMAGE_TO_IMAGE.nickname,
        sub_user_chat_image_model=SEEDREAM_V4_5_EDIT.nickname,
    )
    mock_config = SimpleNamespace(agent=mock_agent)
    with patch(
        "app.core.model_selection.global_config_loaded_from_config_yaml", mock_config
    ):
        model_free = select_chat_image_model(user=user, is_subscribed=False)
        assert model_free is Z_IMAGE_TURBO_IMAGE_TO_IMAGE
        model_sub = select_chat_image_model(user=user, is_subscribed=True)
        assert model_sub is SEEDREAM_V4_5_EDIT
