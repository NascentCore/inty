"""Tests for app.core.voice.tts_api: parse_voice_id, is_gemini_voice, get_gemini_voices (provider prefix)."""

import pytest

from app.core.voice.tts_api import (
    VOICE_ID_PREFIX_ELEVENLABS,
    VOICE_ID_PREFIX_GEMINI,
    get_gemini_voices,
    is_gemini_voice,
    parse_voice_id,
    select_default_gemini_voice_for_imate_gender,
)


class TestParseVoiceId:
    def test_with_google_prefix(self):
        assert parse_voice_id("google/Zephyr") == ("google", "Zephyr")

    def test_with_11labs_prefix(self):
        assert parse_voice_id("11labs/abc123") == ("11labs", "abc123")

    def test_no_prefix(self):
        assert parse_voice_id("Zephyr") == ("", "Zephyr")

    def test_empty_string(self):
        assert parse_voice_id("") == ("", "")

    def test_only_one_slash_splits(self):
        assert parse_voice_id("11labs/id/with/slash") == ("11labs", "id/with/slash")


class TestIsGeminiVoice:
    def test_google_prefix_is_gemini(self):
        assert is_gemini_voice("google/Zephyr") is True
        assert is_gemini_voice("google/Puck") is True

    def test_11labs_prefix_is_not_gemini(self):
        assert is_gemini_voice("11labs/abc") is False

    def test_legacy_gemini_name_no_prefix(self):
        assert is_gemini_voice("Zephyr") is True
        assert is_gemini_voice("Puck") is True

    def test_legacy_elevenlabs_id_no_prefix(self):
        assert is_gemini_voice("JBFqnCBsd6RMkjVDRZzb") is False

    def test_none_or_empty(self):
        assert is_gemini_voice(None) is False
        assert is_gemini_voice("") is False


class TestGetGeminiVoices:
    def test_returns_prefixed_voice_id(self):
        voices = get_gemini_voices()
        assert len(voices) > 0
        for v in voices:
            assert v["voice_id"].startswith(f"{VOICE_ID_PREFIX_GEMINI}/")
            raw = v["voice_id"].split("/", 1)[1]
            assert v["name"] == raw

    def test_first_voice_has_expected_shape(self):
        voices = get_gemini_voices()
        first = voices[0]
        assert first["voice_id"] == f"{VOICE_ID_PREFIX_GEMINI}/{first['name']}"
        assert first["provider"] == "gemini"
        assert first["category"] == "prebuilt"


class TestSelectDefaultGeminiVoiceForImateGender:
    def test_maps_male_to_puck(self):
        assert select_default_gemini_voice_for_imate_gender("MALE") == "Puck"

    def test_maps_female_to_zephyr(self):
        assert select_default_gemini_voice_for_imate_gender("FEMALE") == "Zephyr"

    def test_unknown_gender_falls_back_to_default(self):
        assert select_default_gemini_voice_for_imate_gender("UNKNOWN") == "Zephyr"
