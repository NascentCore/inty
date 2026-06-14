"""Hydrate ai_private splice manifests and tail-splice unsurfaced monolog into LLM dialogue."""

from __future__ import annotations

import uuid
from typing import Any

from app.core.companion_harness.companion.ai_private_prompt import (
    AiPrivateThought,
    load_ai_private_index,
    select_unsurfaced_thoughts_after_anchor,
)
from app.core.companion_harness.companion.dreaming import parse_transcript_datetime
from app.core.companion_harness.companion.models import (
    AI_PRIVATE_HYDRATED_SOURCE,
    AI_PRIVATE_SPLICE_MANIFEST_SOURCE,
    ChatMessage,
    CompanionTurnTrack,
    is_ai_private_splice_manifest,
)
from app.core.companion_harness.companion.proactive_chat import _last_real_user_ts
from app.core.companion_harness.companion.utc import (
    transcript_message_content_for_llm,
    utc_iso_ts,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.transcript_compaction import (
    transcript_rows_to_openai_dialogue,
)

_AI_PRIVATE_SPLICE_TRACKS: frozenset[CompanionTurnTrack] = frozenset(
    {
        CompanionTurnTrack.USER_CHAT,
        CompanionTurnTrack.USER_CHAT_BOOTSTRAP,
        CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT,
    }
)


def track_uses_ai_private_splice(track: CompanionTurnTrack) -> bool:
    """Whether this turn tail-splices unsurfaced ``ai_private`` before the tail user."""
    return track in _AI_PRIVATE_SPLICE_TRACKS


def expand_manifest_rows(
    store: MemoryStore, rows: list[ChatMessage]
) -> list[ChatMessage]:
    """Replace manifest index rows with synthetic assistant monolog from ``ai_private.jsonl``."""
    index = load_ai_private_index(store)
    out: list[ChatMessage] = []
    for row in rows:
        if not is_ai_private_splice_manifest(row):
            out.append(row)
            continue
        uuids = row.ai_private_thought_uuids or []
        for thought_uuid in uuids:
            thought = index.get(thought_uuid)
            if thought is None:
                continue
            out.append(
                ChatMessage(
                    role="assistant",
                    content=thought.text,
                    ts=thought.ts,
                    uuid=thought.uuid,
                    source=AI_PRIVATE_HYDRATED_SOURCE,
                )
            )
    return out


def _last_real_user_uuid(msgs: list[ChatMessage]) -> str | None:
    for row in reversed(msgs):
        if row.role == "user" and row.proactive_chat is not True:
            uuid = row.uuid
            if isinstance(uuid, str) and uuid.strip():
                return uuid.strip()
            return None
    return None


def select_tail_splice_thoughts(
    store: MemoryStore, loaded_transcript: list[ChatMessage]
) -> list[AiPrivateThought]:
    """Unsurfaced monolog after the last real user anchor in ``loaded_transcript``."""
    anchor_ts = _last_real_user_ts(loaded_transcript)
    anchor_uuid = _last_real_user_uuid(loaded_transcript)
    thoughts = select_unsurfaced_thoughts_after_anchor(store, anchor_ts=anchor_ts)
    if anchor_uuid is None:
        return thoughts
    return [
        t
        for t in thoughts
        if t.after_user_msg_uuid is None or t.after_user_msg_uuid == anchor_uuid
    ]


def transcript_window_to_llm_dialogue(
    store: MemoryStore,
    window: list[ChatMessage],
    *,
    tail_splice_thoughts: list[AiPrivateThought],
) -> list[dict[str, Any]]:
    """Expand manifests, map transcript rows, then append tail-spliced monolog assistant rows."""
    expanded = expand_manifest_rows(store, window)
    dialogue = transcript_rows_to_openai_dialogue(expanded)
    for thought in tail_splice_thoughts:
        dialogue.append(
            {
                "role": "assistant",
                "content": transcript_message_content_for_llm(
                    content=thought.text,
                    ts=thought.ts,
                ),
            }
        )
    return dialogue


def build_ai_private_splice_manifest_row(
    *,
    thought_uuids: list[str],
    reply_to_user_msg_uuid: str,
    anchor_user_msg_uuid: str | None,
) -> dict[str, Any]:
    """Manifest index row for ``transcript.jsonl`` (thought UUIDs only, no monolog body)."""
    assert thought_uuids
    assert reply_to_user_msg_uuid.strip()
    row: dict[str, Any] = {
        "role": "system",
        "source": AI_PRIVATE_SPLICE_MANIFEST_SOURCE,
        "content": "[ai_private_splice]",
        "ts": utc_iso_ts(),
        "uuid": str(uuid.uuid4()),
        "reply_to": reply_to_user_msg_uuid.strip(),
        "ai_private_thought_uuids": thought_uuids,
    }
    if anchor_user_msg_uuid is not None:
        row["anchor_user_msg_uuid"] = anchor_user_msg_uuid
    return row


def select_unconsumed_ai_private_for_day(
    store: MemoryStore,
    *,
    day_iso: str,
) -> list[AiPrivateThought]:
    """Unsurfaced ``ai_private.jsonl`` rows whose ``ts`` falls on ``day_iso`` (local calendar)."""
    thoughts = select_unsurfaced_thoughts_after_anchor(store, anchor_ts=None)
    out: list[AiPrivateThought] = []
    for thought in thoughts:
        if parse_transcript_datetime(thought.ts).date().isoformat() == day_iso:
            out.append(thought)
    return sorted(out, key=lambda t: parse_transcript_datetime(t.ts))


def dreaming_transcript_block(
    store: MemoryStore,
    rows: list[ChatMessage],
    *,
    day_iso: str,
) -> str:
    """Render dreaming rollup text: hydrated dialogue plus unconsumed monolog for ``day_iso``."""
    expanded = expand_manifest_rows(store, rows)
    lines: list[str] = []
    for row in expanded:
        if is_ai_private_splice_manifest(row):
            continue
        if row.source == AI_PRIVATE_HYDRATED_SOURCE:
            lines.append(
                f"[{row.ts}] Inner monolog (ai_private): {row.content}"
            )
            continue
        role = "User" if row.role == "user" else "Assistant"
        lines.append(f"[{row.ts}] {role}: {row.content}")
    unconsumed = select_unconsumed_ai_private_for_day(store, day_iso=day_iso)
    if unconsumed:
        lines.append("--- Monolog (ai_private, unconsumed) ---")
        for thought in unconsumed:
            lines.append(
                f"[{thought.ts}] Inner monolog (ai_private): {thought.text}"
            )
    return "\n".join(lines)
