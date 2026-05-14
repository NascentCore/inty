"""Tests for app.core.voice.tts_catalog resolvers and provider checks."""

import pytest

from app.core.voice.tts_api import TTS_PROVIDER_ELEVENLABS, TTS_PROVIDER_GEMINI
from app.core.voice.tts_catalog import (
    CHAT_TTS_GEMINI_MODEL_ALLOWLIST,
    ELEVENLABS_DEFAULT_MODEL_ALLOWLIST,
    GEMINI_2_5_FLASH_TTS,
    GEMINI_2_5_PRO_TTS,
    resolve_tts_model_by_id,
    resolve_tts_model_by_nickname,
    is_model_belongs_to_provider,
    must_resolve_tts_model_by_id,
    must_resolve_tts_model_by_nickname,
)


def test_resolve_tts_model_by_id_returns_spec():
    model = resolve_tts_model_by_id("gemini-2.5-flash-tts")
    assert model is GEMINI_2_5_FLASH_TTS
    assert model.provider == TTS_PROVIDER_GEMINI


def test_resolve_tts_model_by_nickname_returns_spec():
    model = resolve_tts_model_by_nickname("Gemini 2.5 Pro TTS")
    assert model is GEMINI_2_5_PRO_TTS
    assert model.id_on_provider == "gemini-2.5-pro-tts"


def test_must_resolve_tts_model_by_id_unknown_raises():
    with pytest.raises(ValueError, match="not allowed"):
        must_resolve_tts_model_by_id("gemini-unknown-tts")


def test_must_resolve_tts_model_by_nickname_unknown_raises():
    with pytest.raises(ValueError, match="not allowed"):
        must_resolve_tts_model_by_nickname("Unknown TTS Model")


def test_is_model_belongs_to_provider():
    assert is_model_belongs_to_provider("gemini-2.5-flash-tts", TTS_PROVIDER_GEMINI)
    assert is_model_belongs_to_provider(
        "eleven_multilingual_v2", TTS_PROVIDER_ELEVENLABS
    )
    assert not is_model_belongs_to_provider(
        "gemini-2.5-flash-tts", TTS_PROVIDER_ELEVENLABS
    )
    assert not is_model_belongs_to_provider("unknown-model", TTS_PROVIDER_GEMINI)


def test_chat_tts_allowlist_is_gemini_only():
    assert len(CHAT_TTS_GEMINI_MODEL_ALLOWLIST) >= 2
    assert all(
        model.provider == TTS_PROVIDER_GEMINI
        for model in CHAT_TTS_GEMINI_MODEL_ALLOWLIST
    )


def test_elevenlabs_default_allowlist_is_elevenlabs_only():
    assert len(ELEVENLABS_DEFAULT_MODEL_ALLOWLIST) >= 1
    assert all(
        model.provider == TTS_PROVIDER_ELEVENLABS
        for model in ELEVENLABS_DEFAULT_MODEL_ALLOWLIST
    )
