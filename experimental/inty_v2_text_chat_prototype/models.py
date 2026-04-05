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


def is_transcript_real_user_message(m: ChatMessage) -> bool:
    if m.role != "user":
        return False
    if m.heartbeat is True:
        return False
    if m.presence is not None:
        return False
    if m.repl_online_ack is True:
        return False
    return True


def is_transcript_user_reengagement_after_heartbeat(m: ChatMessage) -> bool:
    """
    上一次陪伴心跳 user 行之后：若仅有「REPL 上线 / 会话恢复」而无键入，仍应允许下一次空闲心跳。
    `repl_offline` 不算重新参与。
    """
    if m.role != "user":
        return False
    if m.heartbeat is True:
        return False
    if m.presence == "repl_offline":
        return False
    if is_transcript_real_user_message(m):
        return True
    if m.repl_online_ack is True:
        return True
    if m.presence == "repl_online":
        return True
    return False


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
