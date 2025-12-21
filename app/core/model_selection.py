# CREATED_BY_AGENT: cursor-gpt-5.2 (2025-12-21)

from __future__ import annotations

from app.core.config import global_config_loaded_from_config_yaml
from app.utils.admin import is_superuser_based_on_email


def _is_superuser(user: object) -> bool:
    """
    Best-effort superuser detection that is safe for partially-populated user objects.
    """
    if bool(getattr(user, "is_superuser", False)):
        return True
    email = getattr(user, "email", None)
    return is_superuser_based_on_email(email)


def select_chat_model(*, user: object, is_subscribed: bool) -> str:
    """
    Select chat LLM model based on user's subscription/superuser status.
    """
    config = global_config_loaded_from_config_yaml.agent
    if is_subscribed or _is_superuser(user):
        return config.sub_user_chat_model or config.model
    return config.free_user_chat_model or config.model


def select_text_to_image_model(*, user: object, is_subscribed: bool) -> str:
    """
    Select text-to-image model based on user's subscription/superuser status.
    """
    config = global_config_loaded_from_config_yaml.agent
    if is_subscribed or _is_superuser(user):
        return config.sub_user_text_to_image_model or config.vertex_image_model
    return config.free_user_text_to_image_model or config.vertex_image_model

