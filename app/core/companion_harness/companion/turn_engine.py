"""REPL-grade turn helpers: transcript row persistence via MemoryStore.

TODO(companion-package-reorg): Move this module into a focused sub-package under companion_harness (see issue body for draft layout).
https://github.com/NascentCore/inty/issues/3409"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.companion_harness.memory.memory_store import MemoryStore
from .models import (
    InnerTickActivity,
    transcript_relative_path_for_turn_persistence,
)
from .transcript_assistant_row import (
    TranscriptAssistantRowBuildInput,
    append_transcript_assistant_row,
)
from .utc import utc_iso_ts


def persist_repl_turn_transcript_rows(
    memory_store: MemoryStore,
    *,
    user_text: str,
    assistant_text: str,
    ts_user: str,
    user_msg_uuid: str,
    assistant_reply_to: str,
    repl_online_ack: bool = False,
    inner_tick_turn: bool = False,
    inner_tick_proactive_chat: bool = False,
    assistant_source: str = "chat",
    trace_id: str | None = None,
    assistant_extra: dict[str, Any] | None = None,
    turn_recall: str | None = None,
) -> str:
    """Persist one user + one assistant row to the main or inner-tick JSONL transcript.

    If ``assistant_extra`` is set (typically the parsed envelope metadata dict with
    ``importance_round`` / ``importance_user_message`` / ``importance_assistant_message``), it is
    stored under the assistant row key ``significance_perception`` for parity with ``turn.run_turn``.
    Full importance
    contract: ``dual_llm_chat_branch_envelope`` module docstring.
    """
    rel_tr = transcript_relative_path_for_turn_persistence(
        inner_tick_turn=inner_tick_turn,
        inner_tick_activity=(
            InnerTickActivity.PROACTIVE_CHAT
            if inner_tick_proactive_chat
            else InnerTickActivity.MAINTENANCE
        ),
    )
    store = memory_store
    user_row: dict[str, Any] = {
        "role": "user",
        "content": user_text,
        "ts": ts_user,
        "uuid": user_msg_uuid,
    }
    if inner_tick_turn:
        user_row["inner_tick"] = True
    if inner_tick_proactive_chat:
        # TODO: use enum for message type, not bool proactive_chat
        user_row["proactive_chat"] = True
    if repl_online_ack:
        user_row["repl_online_ack"] = True
    if trace_id is not None and trace_id.strip():
        user_row["trace_id"] = trace_id
    store.append_jsonl_record(rel_tr, user_row)
    assistant_msg_uuid = str(uuid.uuid4())
    append_transcript_assistant_row(
        store,
        rel_tr,
        TranscriptAssistantRowBuildInput(
            content=assistant_text,
            uuid=assistant_msg_uuid,
            reply_to=assistant_reply_to,
            trace_id=trace_id or "",
            source=assistant_source,
            significance_perception=assistant_extra,
            turn_recall=turn_recall,
        ),
        ts=utc_iso_ts(),
    )
    return assistant_msg_uuid
