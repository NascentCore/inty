"""Hydrate ai_private splice manifests and tail-splice unsurfaced monolog into LLM dialogue."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from loguru import logger

from app.core.companion_harness.companion.ai_private_prompt import (
    AiPrivateThought,
    load_ai_private_index,
    mark_ai_private_surfaced,
    select_unsurfaced_thoughts_after_anchor as load_unsurfaced_after_ts,
)
from app.core.companion_harness.companion.models import (
    AI_PRIVATE_HYDRATED_SOURCE,
    AI_PRIVATE_SPLICE_MANIFEST_SOURCE,
    ChatMessage,
    CompanionTurnTrack,
    PROACTIVE_CHAT_SILENT_TOKEN,
    is_ai_private_splice_manifest,
)
from app.core.companion_harness.companion.transcript_anchor import (
    RealUserTranscriptAnchor,
    last_real_user_transcript_anchor,
    parse_transcript_datetime,
)
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
        # TODO(ai-private-splice-scheduled): INNER_TICK_SCHEDULED + GREETING if product wants parity — #3375
    }
)


@dataclass(frozen=True)
class AiPrivateSplicePlan:
    """Tail-splice thoughts selected before prompt build for one turn."""

    thoughts: tuple[AiPrivateThought, ...]
    anchor_user_msg_uuid: str | None


@dataclass(frozen=True)
class AiPrivateSplicePersistInput:
    """Inputs to mark surfaced + append manifest after a successful splice turn."""

    store: MemoryStore
    transcript_relative_path: str
    track: CompanionTurnTrack
    splice_plan: AiPrivateSplicePlan
    user_msg_uuid: str
    assistant_text: str
    bootstrap_skip_final_transcript_assistant_row: bool


def track_uses_ai_private_splice(track: CompanionTurnTrack) -> bool:
    """Whether this turn tail-splices unsurfaced ``ai_private`` before the tail user."""
    return track in _AI_PRIVATE_SPLICE_TRACKS


def _tail_splice_thoughts_at_anchor(
    store: MemoryStore,
    anchor: RealUserTranscriptAnchor,
) -> list[AiPrivateThought]:
    thoughts = load_unsurfaced_after_ts(store, anchor_ts=anchor.ts)
    if anchor.uuid is None:
        return thoughts
    return [
        t
        for t in thoughts
        if t.after_user_msg_uuid is None or t.after_user_msg_uuid == anchor.uuid
    ]


def select_tail_splice_thoughts(
    store: MemoryStore,
    loaded_transcript: list[ChatMessage],
) -> list[AiPrivateThought]:
    """Unsurfaced monolog after the last real user anchor in ``loaded_transcript``."""
    return _tail_splice_thoughts_at_anchor(
        store, last_real_user_transcript_anchor(loaded_transcript)
    )


def build_ai_private_splice_plan(
    store: MemoryStore, loaded_transcript: list[ChatMessage]
) -> AiPrivateSplicePlan:
    anchor = last_real_user_transcript_anchor(loaded_transcript)
    return AiPrivateSplicePlan(
        thoughts=tuple(_tail_splice_thoughts_at_anchor(store, anchor)),
        anchor_user_msg_uuid=anchor.uuid,
    )


def should_persist_ai_private_splice(persist_input: AiPrivateSplicePersistInput) -> bool:
    assistant_text = persist_input.assistant_text.strip()
    return (
        track_uses_ai_private_splice(persist_input.track)
        and persist_input.splice_plan.thoughts
        and assistant_text
        and assistant_text != PROACTIVE_CHAT_SILENT_TOKEN
        and not persist_input.bootstrap_skip_final_transcript_assistant_row
    )


def persist_ai_private_splice_if_applicable(
    persist_input: AiPrivateSplicePersistInput,
) -> None:
    """Mark thoughts surfaced and append manifest row (surfaced before manifest)."""
    if not should_persist_ai_private_splice(persist_input):
        return
    thought_uuids = [t.uuid for t in persist_input.splice_plan.thoughts]
    mark_ai_private_surfaced(persist_input.store, thought_uuids)
    # TODO(ai-private-persist-atomic): surfaced marker + manifest append should share one write batch — #3375
    manifest_row = build_ai_private_splice_manifest_row(
        thought_uuids=thought_uuids,
        reply_to_user_msg_uuid=persist_input.user_msg_uuid,
        anchor_user_msg_uuid=persist_input.splice_plan.anchor_user_msg_uuid,
    )
    persist_input.store.append_jsonl_record(
        persist_input.transcript_relative_path,
        manifest_row,
    )


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
                logger.warning(
                    "ai_private manifest hydrate missing thought uuid={} manifest_uuid={}",
                    thought_uuid,
                    row.uuid,
                )
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


def _thought_uuids_already_in_block(
    expanded: list[ChatMessage], rows: list[ChatMessage]
) -> set[str]:
    uuids: set[str] = set()
    for row in expanded:
        if row.uuid:
            uuids.add(row.uuid)
    for row in rows:
        if not is_ai_private_splice_manifest(row):
            continue
        for thought_uuid in row.ai_private_thought_uuids or []:
            uuids.add(thought_uuid)
    return uuids


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
    exclude_uuids: frozenset[str],
) -> list[AiPrivateThought]:
    """Unsurfaced rows on ``day_iso`` excluding uuids already rendered in the block."""
    thoughts = load_unsurfaced_after_ts(store, anchor_ts=None)
    out: list[AiPrivateThought] = []
    for thought in thoughts:
        if thought.uuid in exclude_uuids:
            continue
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
        if row.source == AI_PRIVATE_HYDRATED_SOURCE:
            lines.append(
                f"[{row.ts}] Inner monolog (ai_private): {row.content}"
            )
            continue
        role = "User" if row.role == "user" else "Assistant"
        lines.append(f"[{row.ts}] {role}: {row.content}")
    exclude = frozenset(_thought_uuids_already_in_block(expanded, rows))
    unconsumed = select_unconsumed_ai_private_for_day(
        store, day_iso=day_iso, exclude_uuids=exclude
    )
    if unconsumed:
        lines.append("--- Monolog (ai_private, unconsumed) ---")
        for thought in unconsumed:
            lines.append(
                f"[{thought.ts}] Inner monolog (ai_private): {thought.text}"
            )
    return "\n".join(lines)
