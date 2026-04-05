"""Pydantic 模型：消息、人格包、控制面元数据。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, BaseModel, Field

from .file_store import read_text
from .memory_store_registry import get_memory_store
from .paths import WorkspacePaths
from .utc import local_date_str


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    ts: str = Field(validation_alias=AliasChoices("ts", "timestamp"))
    uuid: str | None = None
    trace_id: str | None = None
    reply_to: str | None = None
    heartbeat: bool | None = None
    source: str | None = None


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


def _read_memory_document_optional(
    paths: WorkspacePaths,
    relative_path: str,
    *,
    max_chars: int | None = None,
) -> str:
    text = get_memory_store(paths.root).read_document_if_exists(relative_path)
    if text is None:
        return ""
    if max_chars is not None and len(text) > max_chars:
        return text[: max_chars - 1] + "…"
    return text


def _read_memory_document_required(paths: WorkspacePaths, relative_path: str) -> str:
    return get_memory_store(paths.root).read_document(relative_path)


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

    raw_md = ""
    summary_md = ""
    memory_long = _read_memory_document_required(paths, "MEMORY.md")
    if intimate:
        raw_md = _read_memory_document_optional(
            paths,
            f"memory/daily/{day}.md",
            max_chars=_MEMORY_RAW_INJECT_MAX_CHARS,
        )
        summary_md = _read_memory_document_optional(
            paths,
            f"memory/{day}.md",
            max_chars=_MEMORY_DAY_SUMMARY_INJECT_MAX_CHARS,
        )
    else:
        memory_long = ""

    return PromptBundle(
        identity=_read_memory_document_required(paths, "IDENTITY.md"),
        soul=_read_memory_document_required(paths, "SOUL.md"),
        user_md=_read_memory_document_required(paths, "USER.md"),
        memory_md=memory_long,
        agents_md=_read_memory_document_optional(
            paths,
            "AGENTS.md",
            max_chars=_OPTIONAL_DOC_MAX_CHARS,
        ),
        tools_md=_read_memory_document_optional(
            paths,
            "TOOLS.md",
            max_chars=_OPTIONAL_DOC_MAX_CHARS,
        ),
        heartbeat_md=_read_memory_document_optional(
            paths,
            "HEARTBEAT.md",
            max_chars=_OPTIONAL_DOC_MAX_CHARS,
        ),
        memory_raw_diary_today_md=raw_md,
        memory_day_summary_today_md=summary_md,
    )


def load_context_meta(path: Path) -> ContextMeta:
    if not path.is_file():
        return ContextMeta()
    raw_text = read_text(path)
    try:
        raw = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"{path}: invalid JSON in context file") from e
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
TRANSCRIPT_WINDOW_MAX_MESSAGES: int = 20


def transcript_for_llm_turn(loaded: list[ChatMessage]) -> list[ChatMessage]:
    """
    组装送入本轮 chat.completions 的历史消息。
    普通轮与陪伴心跳使用同一尾部窗口，主动回复与现场气氛一致。
    """
    if len(loaded) <= TRANSCRIPT_WINDOW_MAX_MESSAGES:
        return loaded
    return loaded[-TRANSCRIPT_WINDOW_MAX_MESSAGES:]
