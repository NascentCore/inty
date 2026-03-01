"""Tests for models_catalog resolve_nickname, must_resolve_nickname, resolve_id_on_provider and CHAT_IMAGE_GEN_MODELS."""

import pytest

from app.utils.models_catalog import (
    CHAT_IMAGE_FAL_IDS,
    CHAT_IMAGE_FAL_MODELS,
    NANO_BANANA,
    NANO_BANANA_2,
    NANO_BANANA_PRO,
    SEEDREAM_V4_5_EDIT,
    Z_IMAGE_TURBO_IMAGE_TO_IMAGE,
    must_resolve_nickname,
    resolve_id_on_provider,
    resolve_nickname,
)


def test_resolve_nickname_valid_nicknames():
    """允许的 nickname 返回对应的 GenAIModel。"""
    assert resolve_nickname("Nano Banana") is NANO_BANANA
    assert resolve_nickname("Nano Banana 2") is NANO_BANANA_2
    assert resolve_nickname("Nano Banana Pro") is NANO_BANANA_PRO
    assert resolve_nickname("Seedream V4.5 Edit") is SEEDREAM_V4_5_EDIT
    assert resolve_nickname("Z Image Turbo Image to Image") is Z_IMAGE_TURBO_IMAGE_TO_IMAGE


def test_resolve_nickname_returns_id_on_provider():
    """返回的 GenAIModel 可访问 id_on_provider。"""
    model = resolve_nickname("Nano Banana")
    assert model.id_on_provider == NANO_BANANA.id_on_provider
    assert model.id_on_provider == "gemini-2.5-flash-image"


def test_resolve_nickname_unknown_returns_none():
    """未知 nickname 返回 None。"""
    assert resolve_nickname("Unknown Model") is None


def test_must_resolve_nickname_unknown_raises():
    """must_resolve_nickname 对未知 nickname 抛出 ValueError。"""
    with pytest.raises(ValueError) as exc_info:
        must_resolve_nickname("Unknown Model")
    assert "Unknown Model" in str(exc_info.value)
    assert "not allowed" in str(exc_info.value)


def test_resolve_nickname_disallowed_catalog_model_returns_none():
    """不在 CHAT_IMAGE_GEN_MODELS 中的 catalog 模型 nickname 返回 None。"""
    assert resolve_nickname("Imagen 4.0 Fast") is None


def test_resolve_id_on_provider_valid():
    """允许的 id_on_provider 返回对应的 GenAIModel。"""
    assert resolve_id_on_provider(NANO_BANANA.id_on_provider) is NANO_BANANA
    assert resolve_id_on_provider(SEEDREAM_V4_5_EDIT.id_on_provider) is SEEDREAM_V4_5_EDIT


def test_resolve_id_on_provider_unknown_returns_none():
    """未知的 id_on_provider 返回 None。"""
    assert resolve_id_on_provider("unknown-provider-id") is None


def test_chat_image_fal_ids_matches_fal_models():
    """CHAT_IMAGE_FAL_IDS 与 CHAT_IMAGE_FAL_MODELS 的 id_on_provider 一致。"""
    assert CHAT_IMAGE_FAL_IDS == tuple(m.id_on_provider for m in CHAT_IMAGE_FAL_MODELS)
    assert set(CHAT_IMAGE_FAL_IDS) == {
        SEEDREAM_V4_5_EDIT.id_on_provider,
        Z_IMAGE_TURBO_IMAGE_TO_IMAGE.id_on_provider,
    }
