"""Pydantic 模型：消息、人格包、控制面元数据。"""

from __future__ import annotations

import json
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Literal

from loguru import logger
from pydantic import (
    AliasChoices,
    BaseModel,
    Field,
    ValidationError,
    field_validator,
)

from app.core.companion_harness.experience_profile import (
    experience_profile_injects_private_memory,
    normalize_experience_profile_id,
)
from app.core.companion_harness.prompting.bundle import PromptBundle

from .utc import local_date_str
from app.core.companion_harness.memory.memory_store_scope import (
    ensure_template_seeded_core_documents_in_store,
    load_template_seed_text,
)

if TYPE_CHECKING:
    from app.core.companion_harness.memory.memory_store import MemoryStore

AssistantTurnSource = Literal["chat", "inner_tick", "greeting"]


class InnerTickActivity(StrEnum):
    """Idle poll activities serialized on presence ``turn_lock``.

    ``MAINTENANCE`` and ``PROACTIVE_CHAT`` are synthetic **turns** (``run_turn``,
    ``CompanionTurnResult``, optional delivery). ``DREAMING`` is a **memory batch** only
    (``memory_update_during_dreaming``; observability via ``dreaming_observability`` and
    ``inner_tick_activity=dreaming`` on LangSmith / runtime events — not ``CompanionTurnResult``).

    Poll order per wake: proactive → scheduled → maintenance → dreaming (at most one fires;
    see ``inner_tick_poll`` TODO inner-tick-poll-multi-track / #3273).

    TODO(inner-tick-autonomy): Narrow maintenance to autonomy-only — append ``ai_private.jsonl``;
    profile/MemoryDoc sync moves to dreaming. Rename ``MAINTENANCE`` → ``AUTONOMY``.
    """

    MAINTENANCE = "maintenance"
    PROACTIVE_CHAT = "proactive_chat"
    DREAMING = "dreaming"


class CompanionTurnTrack(StrEnum):
    """Active production turn entry tracks (1:1 with ``build_system_messages_for_*``)."""

    USER_CHAT = "user_chat"
    USER_CHAT_BOOTSTRAP = "user_chat_bootstrap"
    IMPLICIT_SIGN_ON_GREETING = "implicit_sign_on_greeting"
    INNER_TICK_PROACTIVE_CHAT = "inner_tick_proactive_chat"
    INNER_TICK_SCHEDULED = "inner_tick_scheduled"
    INNER_TICK_MAINTENANCE = "inner_tick_maintenance"


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


class CompanionTurnResult(BaseModel):
    """One companion kernel turn: visible assistant text plus optional significance scores."""

    assistant_text: str = ""
    significance_perception: dict[str, Any] | None = Field(
        default=None,
        description=(
            "When foreground chat used the dual JSON envelope, parsed importance triple "
            "(importance_round, importance_user_message, importance_assistant_message). "
            "Propagated to transcript JSONL and API meta_data; optional consumer: memory extraction. "
            "See dual_llm_chat_branch_envelope module docstring."
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
    inner_tick_activity: str | None = Field(
        default=None,
        description=(
            "When this turn is an inner-tick synthetic round, ``InnerTickActivity`` value "
            "(``proactive_chat`` / ``maintenance``); mirrored to API/WS "
            "``meta_data.inner_tick_activity``. ``dreaming`` is never set here — see "
            "``dreaming_observability`` runtime events. ``None`` for normal user chat."
        ),
    )
    turn_start_context_mode: str = Field(
        default="",
        description=(
            "context.json experience profile id at the start of this turn "
            "(before tool mutations); mirrored to WS/HTTP assistant meta_data.context_mode."
        ),
    )
    transcript_compaction: dict[str, Any] | None = Field(
        default=None,
        description=(
            "When transcript window compaction ran for this turn (non-inner-tick, feature on), "
            "summary dict: did_compact, reason, char counts, max_context_chars, compaction_count; "
            "mirrored to WS meta_data.transcript_compaction."
        ),
    )
    transcript_user_content: str = Field(
        default="",
        description=(
            "Exact ``content`` written to the user transcript row for this turn (API/chat_history "
            "should mirror this for proactive chat parity)."
        ),
    )


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    ts: str = Field(validation_alias=AliasChoices("ts", "timestamp"))
    uuid: str | None = None
    trace_id: str | None = None
    reply_to: str | None = None
    # TODO: remove validation_alias for heartbeat; no backward compat needed
    proactive_chat: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("proactive_chat", "heartbeat"),
    )
    scheduled: bool | None = None
    presence: PresenceSignal | None = None
    repl_online_ack: bool | None = None
    inner_tick: bool | None = None
    source: str | None = None


_OPTIONAL_DOC_MAX_CHARS = 64_000
_MEMORY_RAW_INJECT_MAX_CHARS = 16_000
_MEMORY_DAY_SUMMARY_INJECT_MAX_CHARS = 12_000
OUTPUT_FORMAT_WECHAT_WEIXIN_MD = "OUTPUT_FORMAT_WECHAT_WEIXIN.md"


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


def _read_memory_document_required(
    store: MemoryStore, relative_path: str
) -> str:
    return store.read_document(relative_path)


def _template_doc_truncated(relative_path: str, *, max_chars: int) -> str:
    text = load_template_seed_text(relative_path).strip()
    if max_chars > 0 and len(text) > max_chars:
        return text[: max_chars - 1] + "..."
    return text


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

    @field_validator("context_mode")
    @classmethod
    def _validate_context_mode(cls, v: str) -> str:
        return normalize_experience_profile_id(v)


def load_prompt_bundle(
    store: MemoryStore,
    *,
    meta: ContextMeta | None = None,
) -> PromptBundle:
    """从 MemoryStore 读取组装 PromptBundle 所需的语义文档。

    私人记忆三层（见 ``memory_taxonomy``）：``memory/daily/<日期>.md`` 情景记忆 episodic，
    ``memory/<日期>.md`` gist 单日摘要，``MEMORY.md`` semantic 语义记忆。
    未启用私人记忆的体验配置时不读取上述日程路径且将 ``MEMORY.md`` 注入留空。"""
    ensure_template_seeded_core_documents_in_store(store)
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
        style_md=_read_memory_document_required(store, "STYLE.md"),
        user_md=_read_memory_document_required(store, "USER.md"),
        memory_md=memory_long,
        techno_core_md=_read_memory_document_optional(store, "TECHNO_CORE.md"),
        living_sphere_md=_read_memory_document_optional(
            store, "LIVING_SPHERE.md"
        ),
        tools_md=_template_doc_truncated(
            "TOOLS.md", max_chars=_OPTIONAL_DOC_MAX_CHARS
        ),
        channels_md=_read_memory_document_required(store, "CHANNELS.md"),
        significance_perception_md=_template_doc_truncated(
            "SIGNIFICANCE_PERCEPTION.md", max_chars=_OPTIONAL_DOC_MAX_CHARS
        ),
        output_format_wechat_weixin_md=_template_doc_truncated(
            OUTPUT_FORMAT_WECHAT_WEIXIN_MD,
            max_chars=_OPTIONAL_DOC_MAX_CHARS,
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
            raise ValueError(
                "context.json: invalid JSON in memory store"
            ) from e
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
            logger.warning(
                "{}: transcript skipped non-object json line", log_label
            )
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
    while (
        i > 0
        and msgs[i - 1].role == "user"
        and msgs[i - 1].presence is not None
    ):
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
    cap = (
        max_messages
        if max_messages is not None
        else TRANSCRIPT_WINDOW_MAX_MESSAGES
    )
    if cap < 1:
        cap = TRANSCRIPT_WINDOW_MAX_MESSAGES
    if len(loaded) <= cap:
        return loaded
    return loaded[-cap:]


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
    inner_tick_activity: InnerTickActivity,
) -> list[ChatMessage]:
    """Transcript rows for assembling this turn's ``messages``.

    Maintenance inner-tick (``InnerTickActivity.MAINTENANCE``) persists only to
    ``transcript_inner_tick.jsonl`` via ``transcript_relative_path_for_turn_persistence``;
    it never appends to ``transcript.jsonl``. User chat and proactive/scheduled inner ticks
    load ``transcript.jsonl`` as-is; maintenance turns merge the inner file for their own LLM
    context.
    """
    raw_main = load_transcript_from_store(store, rel_main_transcript)
    raw_inner = load_transcript_from_store(store, rel_inner_tick_transcript)
    tick_proactive = (
        inner_tick_turn
        and inner_tick_activity == InnerTickActivity.PROACTIVE_CHAT
    )
    if inner_tick_turn and not tick_proactive:
        return merge_transcripts_by_ts(raw_main, raw_inner)
    return raw_main


def transcript_relative_path_for_turn_persistence(
    *,
    inner_tick_turn: bool,
    inner_tick_activity: InnerTickActivity,
) -> str:
    """Scope-relative JSONL path for run_turn user/assistant transcript appends."""
    tick_proactive = (
        inner_tick_turn
        and inner_tick_activity == InnerTickActivity.PROACTIVE_CHAT
    )
    if inner_tick_turn and not tick_proactive:
        # TODO(rename-memory-doc): transcript_inner_tick_maintenance.jsonl (see memory_store_scope).
        # TODO(inner-tick-autonomy): Revisit persistence — autonomy may only need ai_private.jsonl, not a full inner transcript JSONL.
        return "transcript_inner_tick.jsonl"
    return "transcript.jsonl"
