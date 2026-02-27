# CREATED_BY_AGENT: cursor-gpt-5.2 (2025-12-21)

from __future__ import annotations

from app.core.config import global_config_loaded_from_config_yaml
from app.utils.models_catalog import GenAIModel, resolve_chat_image_model


def select_chat_model(*, user: object, is_subscribed: bool) -> str:
    """
    Select chat LLM model based on user's subscription/superuser status.
    """
    config = global_config_loaded_from_config_yaml.agent
    if is_subscribed:
        return config.sub_user_chat_model
    return config.free_user_chat_model


def select_text_to_image_model(*, user: object, is_subscribed: bool) -> str:
    """
    Select text-to-image model based on user's subscription/superuser status.
    """
    config = global_config_loaded_from_config_yaml.agent
    if is_subscribed:
        return config.sub_user_text_to_image_model or config.vertex_image_model
    return config.free_user_text_to_image_model or config.vertex_image_model


def select_chat_image_model(*, user: object, is_subscribed: bool) -> GenAIModel:
    """
    Select chat image (message-to-image) model by subscription only.
    Reads nickname from config and returns the resolved GenAIModel (callers use model.id_on_provider).
    """
    config = global_config_loaded_from_config_yaml.agent
    nickname = (
        config.sub_user_chat_image_model if is_subscribed else config.free_user_chat_image_model
    )
    return resolve_chat_image_model(nickname)
