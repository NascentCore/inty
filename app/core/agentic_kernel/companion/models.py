"""Pydantic 模型：消息、人格包、控制面元数据。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from loguru import logger
from pydantic import AliasChoices, BaseModel, Field, ValidationError

from .file_store import read_text
from .utc import local_date_str

if TYPE_CHECKING:
    from .memory_store import MemoryStore
    from .workspace import WorkspacePaths

PresenceSignal = Literal["repl_online", "repl_offline"]

INNER_TICK_SYNTHETIC_USER_TEXT = (
    "（内在节拍：用户此刻没有键入新内容。这不是请你「对用户接话」的聊天轮，而是一次短时的内在处理——"
    "像在活人头脑里持续活动的那一小团注意：整理刚才的对话与场景印象，掂量哪些值得写入长期材料，"
    "以及在上下文变沉时考虑是否要通过工作区工具做核对、归档或压缩式整理；"
    "同时根据当前对话里的场景与节拍，**轻推下一拍**（一个自然的小进展、未决事的微小落地或情绪上的细微位移），"
    "若上文已自然收束或明显该换景，可**软转场**进入下一情境，避免生硬重开一局。"
    "请结合上文与「内在活动（ai_private）」行事；不要向用户解释本机制，不要提系统、节拍、等待。）"
)

AI_PRIVATE_INJECT_MAX_CHARS = 12_000


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    ts: str = Field(validation_alias=AliasChoices("ts", "timestamp"))
    uuid: str | None = None
    trace_id: str | None = None
    reply_to: str | None = None
    heartbeat: bool | None = None
    presence: PresenceSignal | None = None
    repl_online_ack: bool | None = None
    inner_tick: bool | None = None
    source: str | None = None


_OPTIONAL_DOC_MAX_CHARS = 64_000
_MEMORY_RAW_INJECT_MAX_CHARS = 16_000
_MEMORY_DAY_SUMMARY_INJECT_MAX_CHARS = 12_000


def _read_memory_document_optional(
    store: MemoryStore,
    relative_path: str,
    *,
    max_chars: int | None = None,
) -> str:
    text = store.read_document_if_exists(relative_path)
    if text is None:
        return ""
    if max_chars is not None and len(text) > max_chars:
        return text[: max_chars - 1] + "..."
    return text


def _read_memory_document_required(store: MemoryStore, relative_path: str) -> str:
    return store.read_document(relative_path)


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
    user_id: str = ""
    companion_id: str = ""
    chat_id: str = ""


def load_prompt_bundle(
    paths: WorkspacePaths,
    store: MemoryStore,
    *,
    meta: ContextMeta | None = None,
) -> PromptBundle:
    """加载人格与记忆。非 intimate 模式不读取私人记忆文件。"""
    day = local_date_str()
    m = meta if meta is not None else ContextMeta()
    intimate = m.context_mode.strip().lower() == "intimate"

    raw_md = ""
    summary_md = ""
    memory_long = _read_memory_document_required(store, "MEMORY.md")
    if intimate:
        raw_md = _read_memory_document_optional(
            store,
            f"memory/daily/{day}.md",
            max_chars=_MEMORY_RAW_INJECT_MAX_CHARS,
        )
        summary_md = _read_memory_document_optional(
            store,
            f"memory/{day}.md",
            max_chars=_MEMORY_DAY_SUMMARY_INJECT_MAX_CHARS,
        )
    else:
        memory_long = ""

    return PromptBundle(
        identity=_read_memory_document_required(store, "IDENTITY.md"),
        soul=_read_memory_document_required(store, "SOUL.md"),
        user_md=_read_memory_document_required(store, "USER.md"),
        memory_md=memory_long,
        agents_md=_read_memory_document_optional(
            store,
            "AGENTS.md",
            max_chars=_OPTIONAL_DOC_MAX_CHARS,
        ),
        tools_md=_read_memory_document_optional(
            store,
            "TOOLS.md",
            max_chars=_OPTIONAL_DOC_MAX_CHARS,
        ),
        heartbeat_md=_read_memory_document_optional(
            store,
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


def load_transcript_text(
    text: str, *, log_label: str = "transcript"
) -> list[ChatMessage]:
    out: list[ChatMessage] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            logger.warning("{}: transcript skipped non-json line", log_label)
            continue
        if not isinstance(raw, dict):
            logger.warning("{}: transcript skipped non-object json line", log_label)
            continue
        try:
            out.append(ChatMessage.model_validate(raw))
        except ValidationError:
            logger.warning(
                "{}: transcript skipped invalid ChatMessage row (first 240 chars): {!r}",
                log_label,
                line[:240],
            )
            continue
    return out


def transcript_without_trailing_presence_signals(
    msgs: list[ChatMessage],
) -> list[ChatMessage]:
    i = len(msgs)
    while i > 0 and msgs[i - 1].role == "user" and msgs[i - 1].presence is not None:
        i -= 1
    return msgs[:i]


def load_transcript(path: Path) -> list[ChatMessage]:
    if not path.is_file():
        return []
    return load_transcript_text(read_text(path), log_label=str(path))


def load_transcript_from_store(
    store: MemoryStore, relative_path: str
) -> list[ChatMessage]:
    body = store.read_document_if_exists(relative_path)
    if body is None:
        return []
    return load_transcript_text(body)


# 近期对话窗口
TRANSCRIPT_WINDOW_MAX_MESSAGES: int = 20


def transcript_for_llm_turn(
    loaded: list[ChatMessage], *, max_messages: int | None = None
) -> list[ChatMessage]:
    """组装送入本轮 chat.completions 的历史消息尾部窗口。"""
    cap = max_messages if max_messages is not None else TRANSCRIPT_WINDOW_MAX_MESSAGES
    if cap < 1:
        cap = TRANSCRIPT_WINDOW_MAX_MESSAGES
    if len(loaded) <= cap:
        return loaded
    return loaded[-cap:]
