"""Detect tool_background turns that read convention docs but skip required memory writes.

When the user explicitly asks to change persistent wording or interaction preferences
(e.g. stop using a catchphrase), the tool loop must call ``memory_store_write_document``
after reading USER.md / STYLE.md / SOUL.md / IDENTITY.md — not only read/list and claim
silent persistence in the finish envelope.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.core.companion_harness.tools.companion_tool_definitions import (
    CompanionToolName,
)

_MEMORY_WRITE_TOOL = CompanionToolName.MEMORY_STORE_WRITE_DOCUMENT.value
_MEMORY_READ_TOOL = CompanionToolName.MEMORY_STORE_READ_DOCUMENT.value

_CONVENTION_DOC_NAMES = frozenset(
    {"USER.md", "STYLE.md", "SOUL.md", "IDENTITY.md"},
)

# User turns that ask to stop/avoid specific words or phrasing (persistent preference).
_PERSISTENT_PREFERENCE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"不要.{0,20}说"),
    re.compile(r"别.{0,16}老"),
    re.compile(r"别.{0,16}用"),
    re.compile(r"不要.{0,16}用"),
    re.compile(r"少用"),
    re.compile(r"避讳"),
    re.compile(r"用词雷区"),
    re.compile(r"口头禅"),
)

_TOOL_BG_PERSISTENCE_WRITE_NUDGE = (
    "## 持久化偏好未写入（须补工具调用）\n\n"
    "本回合用户**明确要求**改变相处方式、避讳词或持久偏好；你已读取约定文档，"
    "但尚未调用 ``memory_store_write_document``。\n"
    "**禁止**再输出工具环收尾 JSON；须在**同一条** assistant 消息里先调用 "
    "``memory_store_read_document``（若尚未持有最新全文）再 "
    "``memory_store_write_document`` 覆盖 ``USER.md`` 与/或 ``STYLE.md``（按变更类型），"
    "写入避讳词、重要时刻或风格约束；写完后才可输出收尾 JSON，且 ``output_to_user`` 应为 false。\n"
    "不要口头声称「除名/停用/已记入档案」而未执行 write。"
)


def tool_bg_persistence_write_nudge_text() -> str:
    """System text injected once when the tool loop missed a required memory write."""
    return _TOOL_BG_PERSISTENCE_WRITE_NUDGE


def _message_text(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                raw = block.get("text")
                if isinstance(raw, str):
                    parts.append(raw)
        return "".join(parts)
    if isinstance(content, str):
        return content
    return ""


def last_non_system_user_text(conversation_messages: list[dict[str, Any]]) -> str:
    """Last user message text in the conversation (skips system rows)."""
    for message in reversed(conversation_messages):
        if message.get("role") != "user":
            continue
        return _message_text(message)
    return ""


def user_turn_requires_memory_document_write(user_text: str) -> bool:
    """True when the latest user turn is an explicit persistent-preference change."""
    text = user_text.strip()
    if not text:
        return False
    if text.startswith("[SYSTEM PROACTIVE CHAT]"):
        return False
    return any(pattern.search(text) for pattern in _PERSISTENT_PREFERENCE_PATTERNS)


def _relative_path_from_tool_arguments(raw_arguments: str) -> str | None:
    if not raw_arguments.strip():
        return None
    try:
        payload = json.loads(raw_arguments)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    rel = payload.get("relative_path")
    if isinstance(rel, str) and rel.strip():
        return rel.strip()
    return None


def read_convention_docs_in_tool_loop(
    conversation_messages: list[dict[str, Any]],
) -> bool:
    """True if the loop called memory_store_read_document on a convention markdown doc."""
    for message in conversation_messages:
        if message.get("role") != "assistant":
            continue
        for tool_call in message.get("tool_calls") or []:
            if not isinstance(tool_call, dict):
                continue
            function = tool_call.get("function")
            if not isinstance(function, dict):
                continue
            if function.get("name") != _MEMORY_READ_TOOL:
                continue
            raw_args = function.get("arguments")
            if not isinstance(raw_args, str):
                continue
            rel = _relative_path_from_tool_arguments(raw_args)
            if rel in _CONVENTION_DOC_NAMES:
                return True
    return False


def tool_loop_called_memory_store_write(tool_call_names: list[str]) -> bool:
    return _MEMORY_WRITE_TOOL in tool_call_names


def tool_bg_missing_required_memory_write(
    *,
    conversation_messages: list[dict[str, Any]],
    tool_call_names: list[str],
) -> bool:
    """
    True when the user asked for a persistent preference change, convention docs were
    read in the tool loop, but memory_store_write_document was never called.
    """
    user_text = last_non_system_user_text(conversation_messages)
    if not user_turn_requires_memory_document_write(user_text):
        return False
    if tool_loop_called_memory_store_write(tool_call_names):
        return False
    return read_convention_docs_in_tool_loop(conversation_messages)
