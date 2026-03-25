"""Pydantic 模型：消息、人格包、控制面元数据。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from .file_store import read_text
from .paths import WorkspacePaths
from .utc import local_date_str


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    ts: str


_OPTIONAL_DOC_MAX_CHARS = 64_000
_MEMORY_RAW_INJECT_MAX_CHARS = 16_000
_MEMORY_DAY_SUMMARY_INJECT_MAX_CHARS = 12_000


def _read_optional_text(path: Path, *, max_chars: int | None = None) -> str:
    if not path.is_file():
        return ""
    text = read_text(path)
    if max_chars is not None and len(text) > max_chars:
        return text[: max_chars - 1] + "…"
    return text


class PromptBundle(BaseModel):
    identity: str
    soul: str
    user_md: str
    memory_md: str
    agents_md: str = ""
    tools_md: str = ""
    heartbeat_md: str = ""
    memory_raw_diary_today_md: str = ""
    memory_day_summary_today_md: str = ""


class ContextMeta(BaseModel):
    context_mode: str = "intimate"
    user_id: str = "proto-user-1"
    companion_id: str = "proto-companion-1"
    chat_id: str = "proto-chat-1"


def load_prompt_bundle(
    paths: WorkspacePaths,
    *,
    meta: ContextMeta | None = None,
) -> PromptBundle:
    """加载人格与记忆。非 intimate 模式不读取私人记忆文件（与 prompts 层约定一致）。"""
    day = local_date_str()
    m = meta if meta is not None else ContextMeta()
    intimate = m.context_mode.strip().lower() == "intimate"

    raw_today = paths.memory_raw_diary(day)
    summary_today = paths.memory_day_summary(day)

    raw_md = ""
    summary_md = ""
    memory_long = read_text(paths.memory_md)
    if intimate:
        raw_md = _read_optional_text(
            raw_today, max_chars=_MEMORY_RAW_INJECT_MAX_CHARS
        )
        summary_md = _read_optional_text(
            summary_today, max_chars=_MEMORY_DAY_SUMMARY_INJECT_MAX_CHARS
        )
    else:
        memory_long = ""

    return PromptBundle(
        identity=read_text(paths.identity),
        soul=read_text(paths.soul),
        user_md=read_text(paths.user_md),
        memory_md=read_text(paths.memory_md),
        agents_md=_read_optional_text(
            paths.agents_md, max_chars=_OPTIONAL_DOC_MAX_CHARS
        ),
        tools_md=_read_optional_text(paths.tools_md, max_chars=_OPTIONAL_DOC_MAX_CHARS),
        heartbeat_md=_read_optional_text(
            paths.heartbeat_md, max_chars=_OPTIONAL_DOC_MAX_CHARS
        ),
        memory_raw_diary_today_md=raw_md,
        memory_day_summary_today_md=summary_md,
    )


def load_context_meta(path: Path) -> ContextMeta:
    if not path.is_file():
        return ContextMeta()
    raw = json.loads(read_text(path))
    return ContextMeta.model_validate(raw)


def load_transcript(path: Path) -> list[ChatMessage]:
    if not path.is_file():
        return []
    text = read_text(path)
    out: list[ChatMessage] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(ChatMessage.model_validate_json(line))
    return out


# 近期对话窗口：最多保留的 transcript.jsonl 行数（每行一条 user 或 assistant）
TRANSCRIPT_WINDOW_MAX_MESSAGES: int = 50
