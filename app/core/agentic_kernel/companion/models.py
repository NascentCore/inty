"""Pydantic 模型：消息、人格包、控制面元数据。"""

from __future__ import annotations

import json
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Literal

from loguru import logger
from pydantic import AliasChoices, BaseModel, Field, ValidationError, field_validator

from app.core.agentic_kernel.experience_profile import (
    ExperienceContextMode,
    experience_profile_injects_private_memory,
    normalize_experience_profile_id,
)

from .utc import local_date_str
from .memory_store_scope import load_template_seed_text

if TYPE_CHECKING:
    from .memory_store import MemoryStore

AssistantTurnSource = Literal["chat", "inner_tick"]
CompanionReplyModality = Literal["text", "voice_message"]


class InnerTickMode(StrEnum):
    """Synthetic user-idle turns: maintenance uses restricted tools; proactive_chat is no-tools."""

    MAINTENANCE = "maintenance"
    PROACTIVE_CHAT = "proactive_chat"


PresenceSignal = Literal["repl_online", "repl_offline"]

INNER_TICK_SYNTHETIC_USER_TEXT = (
    "（内在节拍：用户此刻没有键入新内容。这不是请你「对用户接话」的聊天轮，而是一次短时的内在处理——"
    "像在活人头脑里持续活动的那一小团注意：整理刚才的对话与场景印象，掂量哪些值得写入长期材料，"
    "以及在上下文变沉时考虑是否要通过工作区工具做核对、归档或压缩式整理；"
    "同时根据当前对话里的场景与节拍，**轻推下一拍**（一个自然的小进展、未决事的微小落地或情绪上的细微位移），"
    "若上文已自然收束或明显该换景，可**软转场**进入下一情境，避免生硬重开一局。"
    "请结合上文与「内在活动（ai_private）」行事；不要向用户解释本机制，不要提系统、节拍、等待。）"
)

MAINTENANCE_INNER_TICK_CHAT_HISTORY_USER_MARKER = "（内在节拍）"

AI_PRIVATE_INJECT_MAX_CHARS = 12_000


class CompanionTurnResult(BaseModel):
    """One companion kernel turn: visible assistant text plus optional significance scores."""

    assistant_text: str = ""
    reply_modality: CompanionReplyModality = Field(
        default="text",
        description=(
            "Structured envelope intent from dual-LLM chat: normal text bubble vs voice-note "
            "delivery (see significance_perception.DUAL_LLM_CHAT_RESPONSE_FORMAT)."
        ),
    )
    voice_message_script: str = Field(
        default="",
        description=(
            "When reply_modality is voice_message, wording synthesized into the voice clip "
            "(routing layer calls VoiceService); empty for text modality."
        ),
    )
    significance_perception: dict[str, Any] | None = Field(
        default=None,
        description=(
            "When foreground chat used the dual JSON envelope, parsed importance triple "
            "(importance_round, importance_user_message, importance_assistant_message). "
            "Propagated to transcript JSONL and API meta_data; optional consumer: memory extraction. "
            "See significance_perception module docstring."
        ),
    )
    user_msg_uuid: str = ""
    assistant_msg_uuid: str = Field(
        default="",
        description=(
            "Stable id for this assistant reply; matches transcript.jsonl assistant row "
            "`uuid` and API/WS `meta_data.assistant_msg_uuid`."
        ),
    )
    trace_id: str = ""
    langsmith_trace_id: str = ""
    langsmith_run_id: str = ""
    tool_background_started: bool = Field(
        default=False,
        description=(
            "True after start_tool_background_job returned for this turn (background "
            "thread running tool loop). WebSocket foreground preset correlation is "
            "retained until a tool_bg downstream frame is emitted. Successful companion "
            "assistant frames mirror this as meta_data.tool_background_started on the "
            "HTTP/WS payload."
        ),
    )
    assistant_source: AssistantTurnSource = "chat"
    turn_start_context_mode: str = Field(
        default="",
        description=(
            "context.json experience profile id at the start of this turn "
            "(before tool mutations); mirrored to WS/HTTP assistant meta_data.context_mode."
        ),
    )


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


def _template_doc_truncated(relative_path: str, *, max_chars: int) -> str:
    text = load_template_seed_text(relative_path).strip()
    if max_chars > 0 and len(text) > max_chars:
        return text[: max_chars - 1] + "..."
    return text


class PromptBundle(BaseModel):
    identity: str
    soul: str
    user_md: str
    memory_md: str = Field(
        ...,
        description="semantic memory: MEMORY.md body for system injection when private memory is on.",
    )
    living_sphere_md: str = Field(
        default="",
        description="Stable virtual home anchor seeded by living_sphere for TechnoCore presence.",
    )
    significance_perception_md: str = Field(
        default="",
        description=(
            "Operator guidance for 1-10 importance scoring; injected when "
            "include_significance_perception_slice is true (package prompts/SIGNIFICANCE_PERCEPTION.md)."
        ),
    )
    tools_md: str = ""
    memory_raw_diary_today_md: str = Field(
        default="",
        description="episodic memory: memory/daily/<date>.md tail for system injection.",
    )
    memory_day_summary_today_md: str = Field(
        default="",
        description="gist memory: memory/<date>.md for system injection.",
    )


class ContextMeta(BaseModel):
    # Experience profile id (canonical); JSON field name remains context_mode for persistence.
    context_mode: str = "intimate"
    user_id: str = ""
    companion_id: str = ""
    chat_id: str = ""
    # True = skip interactive-bootstrap injection (default for legacy context.json without this key).
    workspace_bootstrap_user_interactive_completed: bool = True
    # True = skip inserting the one-shot WS companion session system line (default for legacy / non-interactive).
    companion_ws_session_system_written: bool = True
    # Legacy JSON flag from older workspaces; WebSocket connect-time kickoff was removed. Default True
    # means "nothing to do"; omit key in new USER_INTERACTIVE seeds.
    companion_ws_interactive_kickoff_sent: bool = True
    # USER_INTERACTIVE seeds only: experience profile to apply after bootstrap completes.
    post_bootstrap_context_mode: str | None = None

    @field_validator("context_mode")
    @classmethod
    def _validate_context_mode(cls, v: str) -> str:
        return normalize_experience_profile_id(v)

    @field_validator("post_bootstrap_context_mode")
    @classmethod
    def _validate_post_bootstrap_context_mode(cls, v: str | None) -> str | None:
        if v is None:
            return None
        n = normalize_experience_profile_id(v)
        if n == ExperienceContextMode.BOOTSTRAP:
            raise ValueError("post_bootstrap_context_mode cannot be 'bootstrap'")
        return n


def load_prompt_bundle(
    store: MemoryStore,
    *,
    meta: ContextMeta | None = None,
) -> PromptBundle:
    """从 MemoryStore 读取组装 PromptBundle 所需的语义文档。

    私人记忆三层（见 ``memory_taxonomy``）：``memory/daily/<日期>.md`` 情景记忆 episodic，
    ``memory/<日期>.md`` gist 单日摘要，``MEMORY.md`` semantic 语义记忆。
    未启用私人记忆的体验配置时不读取上述日程路径且将 ``MEMORY.md`` 注入留空。"""
    day = local_date_str()
    m = meta if meta is not None else ContextMeta()
    inject_private = experience_profile_injects_private_memory(m.context_mode)

    raw_md = ""
    summary_md = ""
    memory_long = _read_memory_document_required(store, "MEMORY.md")
    if inject_private:
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
        living_sphere_md=_read_memory_document_optional(store, "LIVING_SPHERE.md"),
        tools_md=_template_doc_truncated("TOOLS.md", max_chars=_OPTIONAL_DOC_MAX_CHARS),
        significance_perception_md=_template_doc_truncated(
            "SIGNIFICANCE_PERCEPTION.md", max_chars=_OPTIONAL_DOC_MAX_CHARS
        ),
        memory_raw_diary_today_md=raw_md,
        memory_day_summary_today_md=summary_md,
    )


def load_context_meta(*, store: MemoryStore) -> ContextMeta:
    body = store.read_document_if_exists("context.json")
    if body is not None and body.strip():
        try:
            raw = json.loads(body)
        except json.JSONDecodeError as e:
            raise ValueError("context.json: invalid JSON in memory store") from e
        return ContextMeta.model_validate(raw)
    return ContextMeta()


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


def transcript_rows_for_public_chat_llm(rows: list[ChatMessage]) -> list[ChatMessage]:
    """Strip maintenance inner-tick turns from the stream fed to user-facing chat/tool LLM calls."""
    excluded_user_uuids: set[str] = set()
    for m in rows:
        if m.role == "user" and m.inner_tick is True and m.heartbeat is not True:
            uid = m.uuid
            if uid:
                excluded_user_uuids.add(uid)
    out: list[ChatMessage] = []
    for m in rows:
        if m.role == "user" and m.inner_tick is True and m.heartbeat is not True:
            continue
        if m.role == "assistant" and m.reply_to and m.reply_to in excluded_user_uuids:
            continue
        out.append(m)
    return out


def merge_transcripts_by_ts(
    main_rows: list[ChatMessage], inner_rows: list[ChatMessage]
) -> list[ChatMessage]:
    """Chronological merge; equal ``ts`` sorts main-before-inner then original index."""
    tagged: list[tuple[str, int, int, ChatMessage]] = []
    for i, m in enumerate(main_rows):
        tagged.append((m.ts or "", 0, i, m))
    for j, m in enumerate(inner_rows):
        tagged.append((m.ts or "", 1, j, m))
    tagged.sort(key=lambda x: (x[0], x[1], x[2]))
    return [t[3] for t in tagged]


def companion_turn_transcript_loaded_messages(
    store: MemoryStore,
    *,
    rel_main_transcript: str,
    rel_inner_tick_transcript: str,
    inner_tick_turn: bool,
    inner_tick_mode: InnerTickMode,
) -> list[ChatMessage]:
    """Transcript rows for assembling this turn's ``messages`` (public filter + inner file merge)."""
    raw_main = load_transcript_from_store(store, rel_main_transcript)
    raw_inner = load_transcript_from_store(store, rel_inner_tick_transcript)
    public_main = transcript_rows_for_public_chat_llm(raw_main)
    tick_proactive = inner_tick_turn and inner_tick_mode == InnerTickMode.PROACTIVE_CHAT
    if inner_tick_turn and not tick_proactive:
        return merge_transcripts_by_ts(public_main, raw_inner)
    return public_main


def transcript_relative_path_for_turn_persistence(
    *,
    inner_tick_turn: bool,
    inner_tick_mode: InnerTickMode,
) -> str:
    """Scope-relative JSONL path for run_turn user/assistant transcript appends."""
    tick_proactive = inner_tick_turn and inner_tick_mode == InnerTickMode.PROACTIVE_CHAT
    if inner_tick_turn and not tick_proactive:
        return "transcript_inner_tick.jsonl"
    return "transcript.jsonl"
