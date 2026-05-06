"""Unit tests for vision-aware chat model fallback (OpenRouter image_url + text-only catalog)."""

from app.utils.models_catalog import (
    VISION_FALLBACK_CHAT_MODEL_ID,
    catalog_chat_model_supports_image_input,
    resolve_chat_model_to_id,
)
from app.utils.openai_client import openai_messages_include_image_parts


def test_openai_messages_include_image_parts_detects_image_url():
    msgs = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "hi"},
                {"type": "image_url", "image_url": {"url": "https://example.com/x.png"}},
            ],
        }
    ]
    assert openai_messages_include_image_parts(msgs) is True


def test_openai_messages_include_image_parts_false_for_text_only():
    msgs = [{"role": "user", "content": "hello"}]
    assert openai_messages_include_image_parts(msgs) is False


def test_catalog_deepseek_text_only_for_vision_flag():
    mid = resolve_chat_model_to_id("DeepSeek V3.2")
    assert catalog_chat_model_supports_image_input(mid) is False


def test_catalog_gemini_flash_supports_image_input():
    mid = resolve_chat_model_to_id("Gemini 2.5 Flash")
    assert catalog_chat_model_supports_image_input(mid) is True


def test_catalog_unknown_model_returns_none():
    assert catalog_chat_model_supports_image_input("some-org/custom-model") is None


def test_vision_fallback_id_is_gemini_flash():
    assert VISION_FALLBACK_CHAT_MODEL_ID == "google/gemini-2.5-flash"
