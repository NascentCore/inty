# CREATED_BY_AGENT: cursor-gpt-5.2 (2025-12-21)

from __future__ import annotations

from app.core.config import global_config_loaded_from_config_yaml
from app.core.user_privilege.superuser_check import is_superuser


def select_chat_model(*, user: object, is_subscribed: bool) -> str:
    """
    Select chat LLM model based on user's subscription/superuser status.
    """
    config = global_config_loaded_from_config_yaml.agent
    if is_subscribed or is_superuser(user):
        return config.sub_user_chat_model or config.model
    return config.free_user_chat_model or config.model


def select_text_to_image_model(*, user: object, is_subscribed: bool) -> str:
    """
    Select text-to-image model based on user's subscription/superuser status.
    """
    config = global_config_loaded_from_config_yaml.agent
    if is_subscribed or is_superuser(user):
        return config.sub_user_text_to_image_model or config.vertex_image_model
    return config.free_user_text_to_image_model or config.vertex_image_model


def select_chat_image_model(*, user: object, is_subscribed: bool) -> str:
    """
    Select chat image (message-to-image) model based on user's subscription/superuser status.

    Returns:
        "gemini" for Gemini 2.5 Flash Image, or fal model name like "fal-ai/z-image/turbo/image-to-image"
    """
    config = global_config_loaded_from_config_yaml.agent
    if is_subscribed or is_superuser(user):
        return config.sub_user_chat_image_model or "gemini"
    return config.free_user_chat_image_model or "gemini"
