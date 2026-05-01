"""Regression: tool_bg extracts names from appended slice only; NL filler aggregates tool text."""

from app.core.agentic_kernel.companion.tool_background import (
    _extract_tool_call_names,
    _tool_bg_nl_filler_from_appended_turn,
)


def test_extract_tool_call_names_ignores_prior_turn_assistant_tool_calls() -> None:
    history_assistant = {
        "role": "assistant",
        "tool_calls": [
            {
                "id": "old",
                "type": "function",
                "function": {"name": "google_web_search", "arguments": "{}"},
            }
        ],
    }
    this_turn = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "new",
                    "type": "function",
                    "function": {
                        "name": "tool_update_agent_status_line",
                        "arguments": '{"status_line":"x"}',
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "new",
            "content": 'status line updated to "x"',
        },
        {"role": "assistant", "content": ""},
    ]
    full = [history_assistant, *this_turn]
    assert "google_web_search" in _extract_tool_call_names(full)
    assert "google_web_search" not in _extract_tool_call_names(this_turn)
    assert _extract_tool_call_names(this_turn) == ["tool_update_agent_status_line"]


def test_tool_bg_nl_filler_from_appended_turn_status_line() -> None:
    appended = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "c1",
                    "type": "function",
                    "function": {
                        "name": "tool_update_agent_status_line",
                        "arguments": '{"status_line":"hi"}',
                    },
                }
            ],
        },
        {"role": "tool", "tool_call_id": "c1", "content": 'status line updated to "hi"'},
        {"role": "assistant", "content": ""},
    ]
    assert (
        _tool_bg_nl_filler_from_appended_turn(appended)
        == 'status line updated to "hi"'
    )
