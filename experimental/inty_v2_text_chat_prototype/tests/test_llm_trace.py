"""llm_trace 摘要：无网络、仅验证字符串形状。"""

from __future__ import annotations

import sys
from pathlib import Path

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.llm_trace import summarize_messages


def test_summarize_messages_roles_and_lengths() -> None:
    msgs = [
        {"role": "system", "content": "hello\nworld"},
        {"role": "user", "content": "ping"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "read_file", "arguments": '{"path":"a"}'},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call_abc", "content": "file body here"},
    ]
    s = summarize_messages(msgs)
    assert "0:system" in s and "11ch" in s
    assert "1:user 4ch" in s
    assert "2:assistant→[read_file(" in s and "b)" in s
    assert "3:tool" in s and "14ch" in s
