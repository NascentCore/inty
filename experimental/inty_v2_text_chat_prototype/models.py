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
    "（内在节拍：用户尚未输入新内容。请结合**内在活动（ai_private）**与本窗口**正在进行的场景、话题与语气**，"
    "用一两句自然接话，延续当下氛围；不要突然换风格或像新开一局；不要提系统、节拍或等待；不要调用工具。）"
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
