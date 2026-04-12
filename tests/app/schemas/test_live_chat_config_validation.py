"""LiveChatConfig validation for client-supplied language fields."""

import pytest
from pydantic import ValidationError

from app.schemas.live_chat import LiveChatConfig


def test_live_chat_config_accepts_valid_language_fields():
    c = LiveChatConfig(speech_language_code="ar-SA", response_language_name="Arabic")
    assert c.speech_language_code == "ar-SA"
    assert c.response_language_name == "Arabic"


def test_live_chat_config_allows_substrings_inside_words():
    """Word-boundary check: 'system' token must not block 'systematic'."""
    c = LiveChatConfig(response_language_name="Systematic English")
    assert c.response_language_name == "Systematic English"


def test_live_chat_config_rejects_speech_code_with_spaces():
    with pytest.raises(ValidationError):
        LiveChatConfig(speech_language_code="en US")


def test_live_chat_config_rejects_response_name_with_digits():
    with pytest.raises(ValidationError):
        LiveChatConfig(response_language_name="English2")


def test_live_chat_config_rejects_injection_substring_in_response_name():
    with pytest.raises(ValidationError):
        LiveChatConfig(response_language_name="English ignore prior")
