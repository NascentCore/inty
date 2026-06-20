"""Load and append ``ai_private.jsonl`` monolog material for MAINTENANCE and transcript splice.

``ai_private.jsonl`` holds **inner thoughts about the user** (feelings, unsaid lines, scene
beats in the relationship)—not virtual-world activity. Activity in TechnoCore / LivingSphere /
the environment lives in ``LIFE_CURRENTS.md`` (AUTONOMY track).

Structured rows: ``AiPrivateThought`` (``uuid``, ``ts``, ``text``, optional ``after_user_msg_uuid``).
Surfaced consumption appends marker rows ``{kind: surfaced, ref_uuid, ts}`` (append-only).
Kernel maintenance inner-tick turns load history via ``get_ai_private_jsonl_text_for_prompt``;
``get_ai_private_text_for_prompt`` remains for ``ai_private.md`` only (tests, tooling, optional merge).

TODO(companion-package-reorg): Move this module into a focused sub-package under companion_harness (see issue body for draft layout). — #3409
https://github.com/NascentCore/inty/issues/3409"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Literal

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field

from app.core.companion_harness.companion.transcript_anchor import (
    parse_transcript_row_ts as parse_transcript_datetime,
)
from app.core.companion_harness.companion.utc import utc_iso_ts
from app.core.companion_harness.memory.memory_store import MemoryStore

# TODO(rename-memory-doc): Rename ai_private.md to AI_PRIVATE.md — #3400
_AI_PRIVATE_MD_REL = "ai_private.md"

AI_PRIVATE_JSONL_REL = "ai_private.jsonl"

AI_PRIVATE_SURFACED_KIND: Literal["surfaced"] = "surfaced"

AI_PRIVATE_INJECT_MAX_CHARS = 12_000


class AiPrivateThought(BaseModel):
    """One append-only monolog line in ``ai_private.jsonl``."""

    model_config = ConfigDict(frozen=True)

    uuid: str = Field(
        description="Stable id for manifest references and surfaced markers."
    )
    ts: str = Field(
        description="ISO8601 timestamp when the thought was recorded."
    )
    text: str = Field(
        description="Inner monolog text about the user or relationship."
    )
    after_user_msg_uuid: str | None = Field(
        default=None,
        description="Optional anchor to the user message this thought follows.",
    )


class AiPrivateSurfacedMarker(BaseModel):
    """Append-only marker: thought ``ref_uuid`` was consumed by user/proactive splice."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["surfaced"] = AI_PRIVATE_SURFACED_KIND
    ref_uuid: str
    ts: str


def _clip_chars(s: str, cap: int) -> str:
    if cap <= 0:
        return ""
    if len(s) <= cap:
        return s
    return s[: cap - 1] + "..."


def _format_ai_private_jsonl_object(obj: dict[str, Any]) -> str:
    for key in ("text", "content", "note", "body"):
        v = obj.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    try:
        return json.dumps(obj, ensure_ascii=False)
    except TypeError:
        return str(obj)


def _parse_ai_private_jsonl_objects(
    raw: str,
) -> tuple[list[AiPrivateThought], set[str], list[str]]:
    """Return (thoughts, surfaced_uuids, legacy_prompt_lines)."""
    thoughts: list[AiPrivateThought] = []
    surfaced: set[str] = set()
    legacy_lines: list[str] = []
    for i, line in enumerate(raw.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            logger.warning("ai_private.jsonl skipped invalid JSON line {}", i)
            continue
        if not isinstance(obj, dict):
            legacy_lines.append(json.dumps(obj, ensure_ascii=False))
            continue
        if obj.get("kind") == AI_PRIVATE_SURFACED_KIND:
            ref = obj.get("ref_uuid")
            if isinstance(ref, str) and ref.strip():
                surfaced.add(ref.strip())
            continue
        raw_uuid = obj.get("uuid")
        raw_ts = obj.get("ts")
        text = obj.get("text")
        if isinstance(text, str) and text.strip():
            text = text.strip()
        else:
            legacy_text = _format_ai_private_jsonl_object(obj)
            if legacy_text and not (
                isinstance(raw_uuid, str) and isinstance(raw_ts, str)
            ):
                legacy_lines.append(legacy_text)
                continue
            text = legacy_text if legacy_text else ""
        if isinstance(raw_uuid, str) and isinstance(raw_ts, str) and text:
            after = obj.get("after_user_msg_uuid")
            after_uuid = (
                after.strip()
                if isinstance(after, str) and after.strip()
                else None
            )
            thoughts.append(
                AiPrivateThought(
                    uuid=raw_uuid.strip(),
                    ts=raw_ts.strip(),
                    text=text,
                    after_user_msg_uuid=after_uuid,
                )
            )
        elif text:
            legacy_lines.append(text)
    return thoughts, surfaced, legacy_lines


def load_ai_private_thoughts(store: MemoryStore) -> list[AiPrivateThought]:
    """Load non-surfaced structured thoughts from ``ai_private.jsonl``."""
    raw = store.read_document_if_exists(AI_PRIVATE_JSONL_REL)
    if not raw or not raw.strip():
        return []
    thoughts, surfaced, _legacy = _parse_ai_private_jsonl_objects(raw)
    return [t for t in thoughts if t.uuid not in surfaced]


def load_ai_private_index(store: MemoryStore) -> dict[str, AiPrivateThought]:
    """Map thought uuid → row (includes surfaced thoughts for manifest hydrate)."""
    raw = store.read_document_if_exists(AI_PRIVATE_JSONL_REL)
    if not raw or not raw.strip():
        return {}
    thoughts, _surfaced, _legacy = _parse_ai_private_jsonl_objects(raw)
    return {t.uuid: t for t in thoughts}


def mark_ai_private_surfaced(store: MemoryStore, uuids: list[str]) -> None:
    """Append surfaced markers for consumed thought uuids."""
    now = utc_iso_ts()
    for thought_uuid in uuids:
        assert thought_uuid.strip()
        marker = AiPrivateSurfacedMarker(ref_uuid=thought_uuid.strip(), ts=now)
        store.append_jsonl_record(
            AI_PRIVATE_JSONL_REL,
            marker.model_dump(mode="json"),
        )


def append_ai_private_thought(
    store: MemoryStore,
    *,
    text: str,
    after_user_msg_uuid: str | None,
) -> AiPrivateThought:
    """Append one monolog row; server assigns ``uuid`` and ``ts``."""
    assert text.strip()
    thought = AiPrivateThought(
        uuid=str(uuid.uuid4()),
        ts=utc_iso_ts(),
        text=text.strip(),
        after_user_msg_uuid=after_user_msg_uuid,
    )
    store.append_jsonl_record(
        AI_PRIVATE_JSONL_REL,
        thought.model_dump(mode="json", exclude_none=True),
    )
    return thought


def _thought_ts(thought: AiPrivateThought) -> datetime:
    return parse_transcript_datetime(thought.ts)


def select_unsurfaced_thoughts_after_anchor(
    store: MemoryStore,
    *,
    anchor_ts: datetime | None,
) -> list[AiPrivateThought]:
    """Thoughts with ``ts`` strictly after ``anchor_ts``, excluding surfaced."""
    thoughts = load_ai_private_thoughts(store)
    if anchor_ts is None:
        return sorted(thoughts, key=_thought_ts)
    return sorted(
        [t for t in thoughts if _thought_ts(t) > anchor_ts],
        key=_thought_ts,
    )


def get_ai_private_text_for_prompt(
    store: MemoryStore, *, max_chars: int = AI_PRIVATE_INJECT_MAX_CHARS
) -> str:
    """Read ``ai_private.md`` only."""
    body = store.read_document_if_exists(_AI_PRIVATE_MD_REL)
    s = body or ""
    return _clip_chars(s, max_chars)


def get_ai_private_jsonl_text_for_prompt(
    store: MemoryStore, *, max_chars: int = AI_PRIVATE_INJECT_MAX_CHARS
) -> str:
    """Plain lines for MAINTENANCE system injection (unsurfaced + legacy rows)."""
    raw = store.read_document_if_exists(AI_PRIVATE_JSONL_REL)
    if not raw or not raw.strip():
        return ""
    thoughts, surfaced, legacy_lines = _parse_ai_private_jsonl_objects(raw)
    lines_out: list[str] = []
    for t in thoughts:
        if t.uuid in surfaced:
            continue
        lines_out.append(t.text)
    lines_out.extend(legacy_lines)
    merged = "\n".join(lines_out)
    return _clip_chars(merged, max_chars)


def get_ai_private_merged_text_for_prompt(
    store: MemoryStore, *, max_chars: int = AI_PRIVATE_INJECT_MAX_CHARS
) -> str:
    """Concatenate ``ai_private.md`` then ``ai_private.jsonl`` under one character budget."""
    md = get_ai_private_text_for_prompt(store, max_chars=max_chars)
    jl = get_ai_private_jsonl_text_for_prompt(store, max_chars=max_chars)
    if not jl.strip():
        return md
    sep = "\n\n---\n\n（ai_private.jsonl）\n\n"
    combined = md.rstrip() + sep + jl.strip()
    return _clip_chars(combined, max_chars)
