"""Companion intrinsic beat (inner tick): transcript checks and synthetic user text."""

from __future__ import annotations

import time
from pathlib import Path

from .file_store import read_text
from .memory_store import MemoryStore
from .models import ChatMessage, load_transcript_from_store, transcript_without_trailing_presence_signals
from .workspace import WorkspacePaths

INNER_TICK_SYNTHETIC_USER_TEXT = (
    "（内在节拍：用户此刻没有键入新内容。这不是请你「对用户接话」的聊天轮，而是一次短时的内在处理——"
    "像在活人头脑里持续活动的那一小团注意：整理刚才的对话与场景印象，掂量哪些值得写入长期材料，"
    "以及在上下文变沉时考虑是否要通过工作区工具做核对、归档或压缩式整理；"
    "同时根据当前对话里的场景与节拍，**轻推下一拍**（一个自然的小进展、未决事的微小落地或情绪上的细微位移），"
    "若上文已自然收束或明显该换景，可**软转场**进入下一情境，避免生硬重开一局。"
    "请结合上文与「内在活动（ai_private）」行事；不要向用户解释本机制，不要提系统、节拍、等待。）"
)

_AI_PRIVATE_MAX_CHARS = 12_000


def read_ai_private_text_for_inner_tick(workspace: Path) -> str:
    paths = WorkspacePaths(root=workspace.resolve())
    p = paths.ai_private_md
    if not p.is_file():
        return ""
    raw = read_text(p).strip()
    if len(raw) <= _AI_PRIVATE_MAX_CHARS:
        return raw
    return raw[: _AI_PRIVATE_MAX_CHARS - 1] + "..."


def companion_inner_tick_transcript_ready(
    msgs: list[ChatMessage], *, min_transcript_messages: int
) -> bool:
    trimmed = transcript_without_trailing_presence_signals(msgs)
    if len(trimmed) < min_transcript_messages:
        return False
    return bool(trimmed) and trimmed[-1].role == "assistant"


def next_companion_inner_tick_wait_seconds(
    workspace: Path,
    store: MemoryStore,
    *,
    last_inner_fire_monotonic: float | None,
    last_chat_turn_complete_monotonic: float | None,
    first_after_user_seconds: float,
    min_gap_seconds: float,
    min_transcript_messages: int,
    poll_cap_seconds: float,
    blocked_max_seconds: float,
    now_monotonic: float | None = None,
) -> float:
    """
    Seconds until an inner tick may run; <= 0 means eligible now (subject to transcript).
    When workspace not ready for inner tick, returns a short poll-like wait.
    """
    now = now_monotonic if now_monotonic is not None else time.monotonic()
    root = workspace.resolve()
    paths = WorkspacePaths(root=root)
    rel_tr = paths.transcript.relative_to(root).as_posix()
    loaded = load_transcript_from_store(store, rel_tr)

    poll = max(1.0, float(poll_cap_seconds))
    blocked_sleep = min(max(1.0, float(blocked_max_seconds)), poll)

    if not companion_inner_tick_transcript_ready(
        loaded, min_transcript_messages=min_transcript_messages
    ):
        return blocked_sleep

    min_gap = max(0.0, float(min_gap_seconds))
    first_after = max(0.0, float(first_after_user_seconds))

    t_after_user = 0.0
    if last_inner_fire_monotonic is None and last_chat_turn_complete_monotonic is not None:
        t_after_user = max(0.0, first_after - (now - last_chat_turn_complete_monotonic))

    t_after_inner = 0.0
    if last_inner_fire_monotonic is not None:
        t_after_inner = max(0.0, min_gap - (now - last_inner_fire_monotonic))

    need = max(t_after_user, t_after_inner)
    if need <= 0.0:
        return 0.0
    return min(need, poll)
