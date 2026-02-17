# CREATED_BY_AGENT: cursor-gpt-5.2 (2025-12-21)

from __future__ import annotations

from app.core.config import global_config_loaded_from_config_yaml
from app.core.user_privilege.superuser_check import is_superuser
from app.external_services.fal import is_fal_model


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

    Fal models are never returned; Vertex is used instead (fal disabled by policy).
    """
    config = global_config_loaded_from_config_yaml.agent
    if is_subscribed or is_superuser(user):
        model = config.sub_user_text_to_image_model or config.vertex_image_model
    else:
        model = config.free_user_text_to_image_model or config.vertex_image_model
    if is_fal_model(model):
        return config.vertex_image_model
    return model


def select_chat_image_model(*, user: object, is_subscribed: bool) -> str:
    """
    Select chat image (message-to-image) model based on user's subscription/superuser status.

    Fal models are never returned; "gemini" is used instead (fal disabled by policy).
    Returns "gemini" or a non-fal model name.
    """
    config = global_config_loaded_from_config_yaml.agent
    if is_subscribed or is_superuser(user):
        model = config.sub_user_chat_image_model or "gemini"
    else:
        model = config.free_user_chat_image_model or "gemini"
    if is_fal_model(model):
        return "gemini"
    return model
