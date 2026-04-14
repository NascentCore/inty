"""Re-export from kernel companion.models + prototype-compatible load_prompt_bundle."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from app.core.agentic_kernel.companion.models import (  # noqa: F401
    AI_PRIVATE_INJECT_MAX_CHARS,
    INNER_TICK_SYNTHETIC_USER_TEXT,
    TRANSCRIPT_WINDOW_MAX_MESSAGES,
    ChatMessage,
    ContextMeta,
    PresenceSignal,
    PromptBundle,
    load_context_meta,
    load_transcript,
    transcript_for_llm_turn,
    transcript_without_trailing_presence_signals,
)
from app.core.agentic_kernel.companion.models import (
    load_prompt_bundle as _kernel_load_prompt_bundle,
)

from .file_store import read_text, write_text_atomic

REPL_PRESENCE_USER_TEXT_ONLINE = "（系统：用户已在 REPL 上线。）"
REPL_PRESENCE_USER_TEXT_OFFLINE = "（系统：用户已退出 REPL 会话。）"
REPL_ONLINE_ACK_USER_TEXT = "（会话已恢复：请根据上文续接；若无承接点则简短问候即可。）"


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


def undo_trailing_repl_online_presence_line(transcript_path: Path) -> bool:
    if not transcript_path.is_file():
        return False
    text = read_text(transcript_path)
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return False
    try:
        obj = json.loads(lines[-1])
    except json.JSONDecodeError:
        return False
    if obj.get("role") != "user" or obj.get("presence") != "repl_online":
        return False
    kept = lines[:-1]
    new_body = "\n".join(kept) + ("\n" if kept else "")
    write_text_atomic(transcript_path, new_body)
    return True


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
