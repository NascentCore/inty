"""Pydantic 模型：消息、人格包、控制面元数据。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from .file_store import read_text
from .paths import WorkspacePaths


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    ts: str


class PromptBundle(BaseModel):
    identity: str
    soul: str
    user_md: str
    memory_md: str


class ContextMeta(BaseModel):
    context_mode: str = "intimate"
    user_id: str = "proto-user-1"
    companion_id: str = "proto-companion-1"
    chat_id: str = "proto-chat-1"


def load_prompt_bundle(paths: WorkspacePaths) -> PromptBundle:
    return PromptBundle(
        identity=read_text(paths.identity),
        soul=read_text(paths.soul),
        user_md=read_text(paths.user_md),
        memory_md=read_text(paths.memory_md),
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
