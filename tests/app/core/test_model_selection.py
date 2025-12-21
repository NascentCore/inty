# CREATED_BY_AGENT: cursor-gpt-5.2 (2025-12-21)

from types import SimpleNamespace

from app.core.config import GEMINI_2_0_FLASH_LITE, GEMINI_2_5_FLASH
from app.core.config import global_config_loaded_from_config_yaml
from app.core.model_selection import select_chat_model, select_text_to_image_model


def test_select_chat_model_free_user_uses_free_model():
    user = SimpleNamespace(is_superuser=False, email=None)
    model = select_chat_model(user=user, is_subscribed=False)
    assert model == GEMINI_2_0_FLASH_LITE


def test_select_chat_model_subscribed_user_uses_sub_model():
    user = SimpleNamespace(is_superuser=False, email=None)
    model = select_chat_model(user=user, is_subscribed=True)
    assert model == GEMINI_2_5_FLASH


def test_select_chat_model_superuser_uses_sub_model_even_if_not_subscribed():
    user = SimpleNamespace(is_superuser=True, email=None)
    model = select_chat_model(user=user, is_subscribed=False)
    assert model == GEMINI_2_5_FLASH


def test_select_text_to_image_model_defaults_to_vertex_image_model():
    user = SimpleNamespace(is_superuser=False, email=None)
    model = select_text_to_image_model(user=user, is_subscribed=False)
    assert model == global_config_loaded_from_config_yaml.agent.free_user_text_to_image_model

