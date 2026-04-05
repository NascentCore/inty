"""Re-export from kernel companion.models + prototype-compatible load_prompt_bundle."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from app.core.agentic_kernel.companion.models import (  # noqa: F401
    TRANSCRIPT_WINDOW_MAX_MESSAGES,
    ChatMessage,
    ContextMeta,
    PresenceSignal,
    PromptBundle,
    load_context_meta,
    load_transcript,
    transcript_for_llm_turn,
)
from app.core.agentic_kernel.companion.models import (
    load_prompt_bundle as _kernel_load_prompt_bundle,
)

REPL_PRESENCE_USER_TEXT_ONLINE = "（系统：用户已在 REPL 上线。）"
REPL_PRESENCE_USER_TEXT_OFFLINE = "（系统：用户已退出 REPL 会话。）"
REPL_ONLINE_ACK_USER_TEXT = (
    "（会话已恢复：请根据上文续接；若无承接点则简短问候即可。）"
)
INNER_TICK_SYNTHETIC_USER_TEXT = (
    "（内在节拍：用户此刻没有键入新内容。这不是请你「对用户接话」的聊天轮，而是一次短时的内在处理——"
    "像在活人头脑里持续活动的那一小团注意：整理刚才的对话与场景印象，掂量哪些值得写入长期材料，"
    "以及在上下文变沉时考虑是否要通过工作区工具做核对、归档或压缩式整理。"
    "请结合上文与「内在活动（ai_private）」行事；不要向用户解释本机制，不要提系统、节拍、等待。）"
)

AI_PRIVATE_INJECT_MAX_CHARS = 12_000


def is_transcript_real_user_message(m: ChatMessage) -> bool:
    if m.role != "user":
        return False
    if m.heartbeat is True:
        return False
    if m.inner_tick is True:
        return False
    if m.presence is not None:
        return False
    if m.repl_online_ack is True:
        return False
    return True


def transcript_without_trailing_presence_signals(
    msgs: list[ChatMessage],
) -> list[ChatMessage]:
    i = len(msgs)
    while i > 0 and msgs[i - 1].role == "user" and msgs[i - 1].presence is not None:
        i -= 1
    return msgs[:i]


if TYPE_CHECKING:
    from app.core.agentic_kernel.companion.workspace import WorkspacePaths


def load_prompt_bundle(
    paths: WorkspacePaths,
    *,
    meta: ContextMeta | None = None,
) -> PromptBundle:
    """Prototype-compatible wrapper: auto-creates MemoryStore from registry."""
    from .memory_store_registry import get_memory_store

    store = get_memory_store(paths.root)
    return _kernel_load_prompt_bundle(paths, store, meta=meta)
