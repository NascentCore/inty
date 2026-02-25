"""Tests for models_catalog.resolve_chat_image_model and CHAT_IMAGE_MODELS."""

import pytest

from app.utils.models_catalog import (
    CHAT_IMAGE_FAL_IDS,
    CHAT_IMAGE_FAL_MODELS,
    NANO_BANANA,
    NANO_BANANA_PRO,
    SEEDREAM_V4_5_EDIT,
    Z_IMAGE_TURBO_IMAGE_TO_IMAGE,
    resolve_chat_image_model,
)


def test_resolve_chat_image_model_valid_nicknames():
    """允许的 nickname 返回对应的 GenAIModel。"""
    assert resolve_chat_image_model("Nano Banana") is NANO_BANANA
    assert resolve_chat_image_model("Nano Banana Pro") is NANO_BANANA_PRO
    assert resolve_chat_image_model("Seedream V4.5 Edit") is SEEDREAM_V4_5_EDIT
    assert resolve_chat_image_model("Z Image Turbo Image to Image") is Z_IMAGE_TURBO_IMAGE_TO_IMAGE


def test_resolve_chat_image_model_returns_id_on_provider():
    """返回的 GenAIModel 可访问 id_on_provider。"""
    model = resolve_chat_image_model("Nano Banana")
    assert model.id_on_provider == NANO_BANANA.id_on_provider
    assert model.id_on_provider == "gemini-2.5-flash-image"


def test_resolve_chat_image_model_unknown_nickname_raises():
    """未知 nickname 抛出 ValueError。"""
    with pytest.raises(ValueError) as exc_info:
        resolve_chat_image_model("Unknown Model")
    assert "Unknown Model" in str(exc_info.value)
    assert "not allowed" in str(exc_info.value)


def test_resolve_chat_image_model_disallowed_catalog_model_raises():
    """不在 CHAT_IMAGE_MODELS 中的 catalog 模型 nickname 也抛出 ValueError。"""
    with pytest.raises(ValueError) as exc_info:
        resolve_chat_image_model("Imagen 4.0 Fast")
    assert "not allowed" in str(exc_info.value)


def test_chat_image_fal_ids_matches_fal_models():
    """CHAT_IMAGE_FAL_IDS 与 CHAT_IMAGE_FAL_MODELS 的 id_on_provider 一致。"""
    assert CHAT_IMAGE_FAL_IDS == tuple(m.id_on_provider for m in CHAT_IMAGE_FAL_MODELS)
    assert set(CHAT_IMAGE_FAL_IDS) == {
        SEEDREAM_V4_5_EDIT.id_on_provider,
        Z_IMAGE_TURBO_IMAGE_TO_IMAGE.id_on_provider,
    }
