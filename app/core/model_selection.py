# CREATED_BY_AGENT: cursor-gpt-5.2 (2025-12-21)

from __future__ import annotations

from app.core.config import global_config_loaded_from_config_yaml
from app.utils.models_catalog import (
    GenAIModel,
    must_resolve_nickname,
    resolve_chat_model_to_id,
)


def select_chat_model(*, user: object, is_subscribed: bool) -> GenAIModel:
    """
    Select chat LLM model based on user's subscription/superuser status.
    Config may use nickname (e.g. "DeepSeek V3.2") or provider ID; returns ``GenAIModel``
    (use ``.id_on_provider`` for OpenAI-compatible API calls outside the companion harness).
    """
    config = global_config_loaded_from_config_yaml.agent
    raw = config.sub_user_chat_model if is_subscribed else config.free_user_chat_model
    return resolve_chat_text_model(raw)


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
        config.sub_user_chat_image_model
        if is_subscribed
        else config.free_user_chat_image_model
    )
    return must_resolve_nickname(nickname)


def select_chat_music_model(*, user: object, is_subscribed: bool) -> str:
    """
    Select chat music model based on user's subscription status.
    """
    config = global_config_loaded_from_config_yaml.agent
    if is_subscribed:
        return config.sub_user_chat_music_model
    return config.free_user_chat_music_model


def select_chat_tts_model(*, user: object, is_subscribed: bool) -> str:
    """
    Select chat TTS (Gemini TTS) model based on user's subscription status.
    """
    config = global_config_loaded_from_config_yaml.agent
    if is_subscribed:
        return config.sub_user_chat_tts_model
    return config.free_user_chat_tts_model
