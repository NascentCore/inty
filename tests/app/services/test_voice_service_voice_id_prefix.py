"""Tests for VoiceService get_voice_info with provider-prefixed and legacy voice_id."""

import pytest

from app.services.voice_service import VoiceService


@pytest.fixture
def voice_service():
    return VoiceService()


@pytest.mark.asyncio
async def test_get_voice_info_google_prefixed_returns_gemini_voice(voice_service):
    """get_voice_info("google/Zephyr") 应返回 Gemini 预置音色且 voice_id 带前缀。"""
    info = await voice_service.get_voice_info("google/Zephyr")
    assert info is not None
    assert info.get("voice_id") == "google/Zephyr"
    assert info.get("provider") == "gemini"
    assert info.get("name") == "Zephyr"


@pytest.mark.asyncio
async def test_get_voice_info_legacy_zephyr_returns_gemini_voice(voice_service):
    """无前缀的 Zephyr（兼容旧数据）应返回 Gemini 预置音色，返回的 voice_id 带 google/ 前缀。"""
    info = await voice_service.get_voice_info("Zephyr")
    assert info is not None
    assert info.get("voice_id") == "google/Zephyr"
    assert info.get("provider") == "gemini"
    assert info.get("name") == "Zephyr"
