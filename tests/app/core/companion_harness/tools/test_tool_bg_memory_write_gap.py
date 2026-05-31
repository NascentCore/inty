"""tool_background missing memory_store_write_document detection."""

from __future__ import annotations

from app.core.companion_harness.tools.tool_bg_memory_write_gap import (
    read_convention_docs_in_tool_loop,
    tool_bg_missing_required_memory_write,
    user_turn_requires_memory_document_write,
)


def test_user_turn_requires_write_for_catchphrase_ban() -> None:
    assert user_turn_requires_memory_document_write(
        '不要老是说"抓到"，你是比我强大的多的智能体'
    )


def test_user_turn_skips_proactive_chat_marker() -> None:
    assert not user_turn_requires_memory_document_write(
        "[SYSTEM PROACTIVE CHAT] Time since the user's last message: 2m"
    )


def test_missing_write_when_read_user_style_without_write() -> None:
    messages = [
        {"role": "user", "content": "别老用捏这个字"},
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "tc1",
                    "type": "function",
                    "function": {
                        "name": "memory_store_read_document",
                        "arguments": '{"relative_path":"USER.md"}',
                    },
                }
            ],
        },
        {"role": "tool", "tool_call_id": "tc1", "content": "# USER"},
    ]
    assert tool_bg_missing_required_memory_write(
        conversation_messages=messages,
        tool_call_names=["memory_store_read_document"],
    )


def test_not_missing_after_write() -> None:
    messages = [
        {"role": "user", "content": "不要说抓到"},
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "tc1",
                    "type": "function",
                    "function": {
                        "name": "memory_store_write_document",
                        "arguments": '{"relative_path":"USER.md","content":"# USER"}',
                    },
                }
            ],
        },
    ]
    assert not tool_bg_missing_required_memory_write(
        conversation_messages=messages,
        tool_call_names=["memory_store_write_document"],
    )


def test_read_convention_docs_detects_style_path() -> None:
    messages = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "tc1",
                    "type": "function",
                    "function": {
                        "name": "memory_store_read_document",
                        "arguments": '{"relative_path":"STYLE.md"}',
                    },
                }
            ],
        },
    ]
    assert read_convention_docs_in_tool_loop(messages)
