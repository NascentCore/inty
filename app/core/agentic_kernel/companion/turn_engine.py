"""REPL-grade turn helpers: message assembly and transcript rows via MemoryStore."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from .memory_registry import get_memory_store
from .message_format import TRANSCRIPT_MSG_UUID_KEY
from .models import ChatMessage, ContextMeta, PromptBundle
from .prompts import build_system_prompt
from .utc import utc_iso_ts
from .workspace import WorkspacePaths


def build_repl_turn_base_messages(
    *,
    bundle: PromptBundle,
    context: ContextMeta,
    transcript: list[ChatMessage],
    user_text: str,
    repl_online_ack_turn: bool = False,
    inner_tick_turn: bool = False,
    ai_private_text: str = "",
) -> tuple[list[dict[str, Any]], str]:
    system = build_system_prompt(
        bundle,
        context,
        enable_user_profile_tool=True,
        inner_tick_turn=inner_tick_turn,
        repl_online_ack_turn=repl_online_ack_turn,
        ai_private_text=ai_private_text,
    )
    messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for m in transcript:
        row: dict[str, Any] = {"role": m.role, "content": m.content}
        if m.uuid:
            row[TRANSCRIPT_MSG_UUID_KEY] = m.uuid
        messages.append(row)
    user_msg_uuid = str(uuid.uuid4())
    messages.append(
        {
            "role": "user",
            "content": user_text,
            TRANSCRIPT_MSG_UUID_KEY: user_msg_uuid,
        }
    )
    return messages, user_msg_uuid


def persist_repl_turn_transcript_rows(
    workspace_root: Path,
    *,
    user_text: str,
    assistant_text: str,
    ts_user: str,
    user_msg_uuid: str,
    assistant_reply_to: str,
    repl_online_ack: bool = False,
    inner_tick_turn: bool = False,
    assistant_source: str = "chat",
    trace_id: str | None = None,
) -> str:
    root = workspace_root.resolve()
    paths = WorkspacePaths(root=root)
    rel_tr = paths.transcript.relative_to(root).as_posix()
    store = get_memory_store(root)
    user_row: dict[str, Any] = {
        "role": "user",
        "content": user_text,
        "ts": ts_user,
        "uuid": user_msg_uuid,
    }
    if inner_tick_turn:
        user_row["inner_tick"] = True
    if repl_online_ack:
        user_row["repl_online_ack"] = True
    if trace_id is not None and trace_id.strip():
        user_row["trace_id"] = trace_id
    store.append_jsonl_record(rel_tr, user_row)
    assistant_msg_uuid = str(uuid.uuid4())
    store.append_jsonl_record(
        rel_tr,
        {
            "role": "assistant",
            "content": assistant_text,
            "ts": utc_iso_ts(),
            "uuid": assistant_msg_uuid,
            "reply_to": assistant_reply_to,
            "source": assistant_source,
            "trace_id": trace_id,
        },
    )
    return assistant_msg_uuid
