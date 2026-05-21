"""Tests for generate_voice_message companion tool."""

from __future__ import annotations

import asyncio
import json

import pytest

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.tools.companion_tool_runtime import execute_tool_call
from app.core.config import global_config_loaded_from_config_yaml
from app.services.agent_status_line import (
    clear_tool_background_voice_ctx,
    set_tool_background_voice_ctx,
)


def _run_tool(store: MemoryStore, name: str, args: str) -> str:
    return asyncio.run(execute_tool_call(store, name, args))


def test_generate_voice_message_empty_transcript_errors(tmp_path) -> None:
    st = MemoryStore(
        scope=CompanionScope("tools", "a", f"{tmp_path.name}-voice-err"),
        repository=None,
    )
    set_tool_background_voice_ctx(
        {
            "chat_voice_id": "test-voice",
            "language": "en",
        }
    )
    try:
        out = _run_tool(
            st,
            "generate_voice_message",
            json.dumps({"transcript": "   "}),
        )
        assert out.startswith("ERROR:")
    finally:
        clear_tool_background_voice_ctx()


def test_generate_voice_message_missing_voice_ctx_errors(tmp_path) -> None:
    st = MemoryStore(
        scope=CompanionScope("tools", "a", f"{tmp_path.name}-voice-ctx"),
        repository=None,
    )
    clear_tool_background_voice_ctx()
    out = _run_tool(
        st,
        "generate_voice_message",
        json.dumps({"transcript": "hello"}),
    )
    assert out == "ERROR: voice context not available for TTS"


@pytest.mark.skipif(
    not global_config_loaded_from_config_yaml.tts.use_fake_tts,
    reason="requires fake TTS in config",
)
def test_generate_voice_message_success_returns_audio_url(tmp_path) -> None:
    st = MemoryStore(
        scope=CompanionScope("tools", "a", f"{tmp_path.name}-voice-ok"),
        repository=None,
    )
    set_tool_background_voice_ctx(
        {
            "chat_voice_id": "test-voice-id",
            "language": "en",
        }
    )
    try:
        out = _run_tool(
            st,
            "generate_voice_message",
            json.dumps({"transcript": "hello there"}),
        )
        assert out.startswith("OK ")
        assert "audio_url=" in out
        audio_url = out.split("audio_url=", 1)[1].split()[0]
        if global_config_loaded_from_config_yaml.gcs.use_fake_gcs:
            assert audio_url.startswith("file://")
        else:
            assert audio_url.startswith("https://storage.googleapis.com/")
        assert "duration_seconds=" in out
    finally:
        clear_tool_background_voice_ctx()
