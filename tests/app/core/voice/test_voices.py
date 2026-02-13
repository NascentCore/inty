"""Tests for app.core.voice.voices (VoiceMetadata, list_gemini_voices)."""

import pytest

from app.core.voice.voices import VoiceMetadata, list_gemini_voices


def test_list_gemini_voices_non_empty():
    """list_gemini_voices 返回非空列表。"""
    voices = list_gemini_voices()
    assert isinstance(voices, list)
    assert len(voices) > 0


def test_list_gemini_voices_returns_voice_metadata():
    """list_gemini_voices 的每一项为 VoiceMetadata，且包含预期字段。"""
    voices = list_gemini_voices()
    assert len(voices) > 0
    first = voices[0]
    assert isinstance(first, VoiceMetadata)
    assert hasattr(first, "voice_id")
    assert hasattr(first, "name")
    assert hasattr(first, "gender")
    assert hasattr(first, "provider")
    assert hasattr(first, "source")
    assert hasattr(first, "category")
    assert hasattr(first, "preview_url")
    assert isinstance(first.voice_id, str)
    assert isinstance(first.name, str)
    assert first.voice_id == first.name  # Gemini 预置音色 voice_id 与 name 一致
    assert first.provider == "gemini"
    assert first.category == "prebuilt"
    assert first.source == "preset"
    assert first.preview_url.startswith("http")
