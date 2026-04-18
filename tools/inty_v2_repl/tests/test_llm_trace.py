"""llm_trace 摘要：无网络、仅验证字符串形状。"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

_EXPERIMENTAL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_EXPERIMENTAL))

from inty_v2_repl.llm_trace import (
    LLM_TRACE_JSONL_VERSION,
    TRANSCRIPT_MSG_UUID_KEY,
    configure_llm_trace_file,
    emit_trace,
    is_system_prompt_bundle,
    summarize_messages,
    summarize_system_message_content,
)
from inty_v2_repl.prompts import (
    SYSTEM_PROMPT_SEP,
    system_prompt_security_prefix,
)


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
            "## AGENTS（工作空间约定）\n\nagents",
            "## IDENTITY\n\ni",
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
    assert "myws/AGENTS.md" in s
    assert "myws/IDENTITY.md" in s
    assert "myws/context.json" in s
    assert "myws/output_contract" in s
    assert "«" not in s


def test_summarize_messages_transcript_uuid_refs_skip_angle_preview() -> None:
    uid = "11111111-1111-1111-1111-111111111111"
    aid = "22222222-2222-2222-2222-222222222222"
    msgs = [
        {"role": "system", "content": "x"},
        {
            "role": "user",
            "content": "secret user line",
            TRANSCRIPT_MSG_UUID_KEY: uid,
        },
        {
            "role": "assistant",
            "content": "secret assistant line",
            TRANSCRIPT_MSG_UUID_KEY: aid,
        },
    ]
    s = summarize_messages(msgs, "ws", "2026-01-01")
    assert f"1:user transcript⟨{uid}⟩" in s
    assert f"2:assistant transcript⟨{aid}⟩" in s
    assert "secret" not in s


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


def test_emit_trace_writes_one_jsonl_line_to_file(tmp_path: Path) -> None:
    log = tmp_path / "trace.jsonl"
    try:
        configure_llm_trace_file(log)
        emit_trace(
            "test.where",
            round_idx=2,
            model="m",
            messages="0:user 1ch «x»",
            response="finish=stop text 0ch «»",
            trace_id="trace-123",
        )
        lines = log.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        row = json.loads(lines[0])
        assert row["v"] == LLM_TRACE_JSONL_VERSION
        assert row["kind"] == "llm_trace"
        assert row["where"] == "test.where"
        assert row["round_idx"] == 2
        assert row["model"] == "m"
        assert row["req"] == "0:user 1ch «x»"
        assert row["resp"] == "finish=stop text 0ch «»"
        assert row["trace_id"] == "trace-123"
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


def test_emit_trace_omits_empty_trace_id() -> None:
    with tempfile.TemporaryDirectory() as td:
        log = Path(td) / "trace.jsonl"
        try:
            configure_llm_trace_file(log)
            emit_trace(
                "noop",
                round_idx=1,
                model="m",
                messages="x",
                response="y",
                trace_id="   ",
            )
            lines = log.read_text(encoding="utf-8").splitlines()
            assert len(lines) == 1
            row = json.loads(lines[0])
            assert "trace_id" not in row
        finally:
            configure_llm_trace_file(None)
