"""llm_trace 摘要：无网络、仅验证字符串形状。"""

from __future__ import annotations

import sys
from pathlib import Path

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_text_chat_prototype.llm_trace import (
    configure_llm_trace_file,
    emit_trace,
    is_system_prompt_bundle,
    summarize_messages,
    summarize_system_message_content,
)
from inty_v2_text_chat_prototype.prompts import SYSTEM_PROMPT_SEP, system_prompt_security_prefix


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
    s = summarize_messages(msgs, "tws", "2026-01-01")
    assert "0:system" in s and "11ch" in s
    assert "1:user 4ch" in s
    assert "2:assistant→[read_file(" in s and "b)" in s
    assert "3:tool" in s and "14ch" in s


def test_summarize_messages_bundle_system_uses_refs_not_angle_quote_preview() -> None:
    sep = SYSTEM_PROMPT_SEP
    sys_content = sep.join(
        [
            system_prompt_security_prefix(),
            "## IDENTITY\n\ni",
            "## CAPABILITIES（基础能力与限制）\n\ncap",
            "## SOUL\n\ns",
            "当前上下文模式：亲密主会话。可加载完整长期记忆，语气可更放松、贴近私人对话，仍须遵守安全与同意边界。",
            "## USER\n\nu",
            "输出与工具：仅测试契约首行。",
        ]
    )
    assert is_system_prompt_bundle(sys_content)
    msgs = [{"role": "system", "content": sys_content}]
    s = summarize_messages(msgs, "myws", "2026-03-25")
    assert "0:system" in s
    assert "@⟨" in s
    assert "myws/security" in s
    assert "myws/IDENTITY.md" in s
    assert "myws/context.json" in s
    assert "myws/CAPABILITIES.md" in s
    assert "myws/output_contract" in s
    assert "«" not in s


def test_summarize_system_message_content_labels_memory_paths_with_day() -> None:
    sep = SYSTEM_PROMPT_SEP
    sys_content = sep.join(
        [
            system_prompt_security_prefix(),
            "## MEMORY 日记（今日原始）\n\nd",
            "## MEMORY 当日总结\n\nx",
            "## MEMORY（长期记忆定稿）\n\nm",
            "输出通道：仅文本。",
        ]
    )
    out = summarize_system_message_content(sys_content, ws_label="w", day="2026-04-01")
    assert "w/memory/daily/2026-04-01.md" in out
    assert "w/memory/2026-04-01.md" in out
    assert "w/MEMORY.md" in out


def test_emit_trace_writes_three_lines_to_file(tmp_path: Path) -> None:
    log = tmp_path / "trace.log"
    try:
        configure_llm_trace_file(log)
        emit_trace(
            "test.where",
            round_idx=2,
            model="m",
            messages="0:user 1ch «x»",
            response="finish=stop text 0ch «»",
        )
        text = log.read_text(encoding="utf-8")
        lines = text.splitlines()
        assert len(lines) == 3
        assert lines[0].startswith("[llm-trace] test.where #2 model=m")
        assert lines[1].startswith("[llm-trace]   req:")
        assert lines[2].startswith("[llm-trace]   resp:")
    finally:
        configure_llm_trace_file(None)


def test_emit_trace_no_file_configured_does_not_raise() -> None:
    configure_llm_trace_file(None)
    try:
        emit_trace(
            "noop",
            round_idx=1,
            model="m",
            messages="x",
            response="y",
        )
    finally:
        configure_llm_trace_file(None)
