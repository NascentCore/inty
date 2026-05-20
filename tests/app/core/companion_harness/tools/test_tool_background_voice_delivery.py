"""Tests for tool_background voice GENERATION deliver and audio URL parsing."""

from __future__ import annotations

from app.core.companion_harness.tools.tool_background import (
    ToolOutputEvent,
    _audio_urls_from_tool_messages,
    _generation_tool_execution_deliver,
)


def test_audio_urls_from_tool_messages_parses_ok_line() -> None:
    messages = [
        {
            "role": "tool",
            "content": "OK audio_url=https://storage.googleapis.com/b/o.mp3 duration_seconds=1.5",
        },
    ]
    assert _audio_urls_from_tool_messages(messages) == [
        "https://storage.googleapis.com/b/o.mp3"
    ]


def test_generation_deliver_true_when_only_audio_success() -> None:
    appended = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "tc1",
                    "function": {"name": "generate_voice_message"},
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "tc1",
            "content": "OK audio_url=https://example.com/a.mp3 duration_seconds=2",
        },
    ]
    assert _generation_tool_execution_deliver(
        appended,
        ["generate_voice_message"],
        [],
        ["https://example.com/a.mp3"],
    )


def test_tool_output_event_accepts_precomputed_audio_url() -> None:
    ev = ToolOutputEvent(
        scope_registry_key="k",
        memory_store=None,  # type: ignore[arg-type]
        user_msg_uuid="u",
        assistant_msg_uuid="a",
        text="",
        ts="t",
        elapsed_ms=1,
        precomputed_audio_url="https://example.com/v.mp3",
        generation_deliver=True,
    )
    assert ev.precomputed_audio_url == "https://example.com/v.mp3"
