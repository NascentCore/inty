"""Map logical document paths (scope-relative) to ORM (document_kind, calendar_date)."""

from __future__ import annotations

import re
from datetime import date
from enum import Enum
from typing import Final

from .memory_store_path_constants import (
    AI_PRIVATE_JSONL_REL,
    AI_PRIVATE_MD_REL,
    CHANNELS_MD_REL,
    COMPANION_CONTEXT_COMPACTION_STATE_JSON_REL,
    COMPANION_DREAMING_STATE_JSON_REL,
    COMPANION_LIVING_SPHERE_CURATOR_JSON_REL,
    COMPANION_RUNTIME_EVENTS_JSONL_REL,
    COMPANION_SCHEDULE_TASKS_JSON_REL,
    COMPANION_USER_FEEDBACK_JSONL_REL,
    COMPANIONSHIP_MD_REL,
    CONTEXT_JSON_REL,
    GENERATED_IMAGES_INDEX_JSONL_REL,
    IDENTITY_MD_REL,
    INTY_V2_CONTEXT_COMPACTION_STATE_JSON_REL,
    INTY_V2_LIVING_SPHERE_CURATOR_JSON_REL,
    INTY_V2_SCHEDULE_TASKS_JSON_REL,
    LIFE_CURRENTS_MD_REL,
    LIVING_SPHERE_MD_REL,
    LIVING_SPHERE_UPDATES_JSONL_REL,
    MEMORY_MD_REL,
    SIGNIFICANCE_PERCEPTION_MD_REL,
    SOUL_MD_REL,
    STYLE_MD_REL,
    TECHNO_CORE_EVENTS_JSONL_REL,
    TECHNO_CORE_MD_REL,
    TOOL_BACKGROUND_JSONL_REL,
    TOOLS_MD_REL,
    TRANSCRIPT_INNER_TICK_JSONL_REL,
    TRANSCRIPT_JSONL_REL,
    USER_MD_REL,
)

_MEMORY_DAILY_RE: Final[re.Pattern[str]] = re.compile(
    r"^memory/daily/(\d{4}-\d{2}-\d{2})\.md$", re.IGNORECASE
)


class CompanionMemoryDocumentKind(str, Enum):
    """Persisted document discriminator (no DB path columns).

    TODO(memory-hierarchy-design): After #3405, map kinds to agreed logical memory layers
    (design doc only in that issue—do not assume a preset taxonomy here).
    """

    IDENTITY = "identity"
    SOUL = "soul"
    STYLE = "style"
    USER = "user"
    MEMORY = "memory"
    LIFE_CURRENTS = "life_currents"
    CHANNELS = "channels"
    COMPANIONSHIP = "companionship"
    TECHNO_CORE = "techno_core"
    # TODO(world-engine-firefly-kind): Add FIREFLY sub-agent hidden-state document kind — #3704
    TECHNO_CORE_EVENTS_JSONL = "techno_core_events_jsonl"
    LIVING_SPHERE = "living_sphere"
    LIVING_SPHERE_UPDATES_JSONL = "living_sphere_updates_jsonl"
    TOOLS = "tools"
    # TODO(static-prompt-slice-memstore): Add HARNESS + OUTPUT_FORMAT_IM_DM kinds; load static — #3506
    # Capability slices from MemoryStore, not _template_doc_truncated. !3506
    # Package seed SIGNIFICANCE_PERCEPTION.md; scoring semantics consumed via PromptBundle, not ORM-only.
    SIGNIFICANCE_PERCEPTION = "significance_perception"
    TRANSCRIPT = "transcript"
    TRANSCRIPT_INNER_TICK = "transcript_inner_tick"
    CONTEXT_JSON = "context_json"
    AI_PRIVATE_MD = "ai_private_md"
    AI_PRIVATE_JSONL = "ai_private_jsonl"
    TOOL_BACKGROUND_JSONL = "tool_background_jsonl"
    GENERATED_IMAGES_INDEX_JSONL = "generated_images_index_jsonl"
    MEMORY_DAILY_RAW = (
        "memory_daily_raw"  # daily gist: memory/daily/<date>.md (dreaming only)
    )
    COMPANION_LIVING_SPHERE_CURATOR_JSON = (
        "companion_living_sphere_curator_json"
    )
    COMPANION_CONTEXT_COMPACTION_STATE_JSON = (
        "companion_context_compaction_state_json"
    )
    COMPANION_SCHEDULE_TASKS_JSON = "companion_schedule_tasks_json"
    COMPANION_RUNTIME_EVENTS_JSONL = "companion_runtime_events_jsonl"
    COMPANION_USER_FEEDBACK_JSONL = "companion_user_feedback_jsonl"
    COMPANION_DREAMING_STATE_JSON = "companion_dreaming_state_json"
    INTY_V2_LIVING_SPHERE_CURATOR_JSON = "inty_v2_living_sphere_curator_json"
    INTY_V2_CONTEXT_COMPACTION_STATE_JSON = (
        "inty_v2_context_compaction_state_json"
    )
    INTY_V2_SCHEDULE_TASKS_JSON = "inty_v2_schedule_tasks_json"


_REL_TO_KIND: dict[str, tuple[CompanionMemoryDocumentKind, date | None]] = {
    IDENTITY_MD_REL: (CompanionMemoryDocumentKind.IDENTITY, None),
    SOUL_MD_REL: (CompanionMemoryDocumentKind.SOUL, None),
    STYLE_MD_REL: (CompanionMemoryDocumentKind.STYLE, None),
    USER_MD_REL: (CompanionMemoryDocumentKind.USER, None),
    MEMORY_MD_REL: (CompanionMemoryDocumentKind.MEMORY, None),
    # Virtual-space activity state (AUTONOMY): what Inty is doing in the world—not inner thoughts about the user.
    LIFE_CURRENTS_MD_REL: (CompanionMemoryDocumentKind.LIFE_CURRENTS, None),
    CHANNELS_MD_REL: (CompanionMemoryDocumentKind.CHANNELS, None),
    COMPANIONSHIP_MD_REL: (CompanionMemoryDocumentKind.COMPANIONSHIP, None),
    TECHNO_CORE_MD_REL: (CompanionMemoryDocumentKind.TECHNO_CORE, None),
    TECHNO_CORE_EVENTS_JSONL_REL: (
        CompanionMemoryDocumentKind.TECHNO_CORE_EVENTS_JSONL,
        None,
    ),
    LIVING_SPHERE_MD_REL: (CompanionMemoryDocumentKind.LIVING_SPHERE, None),
    LIVING_SPHERE_UPDATES_JSONL_REL: (
        CompanionMemoryDocumentKind.LIVING_SPHERE_UPDATES_JSONL,
        None,
    ),
    TOOLS_MD_REL: (CompanionMemoryDocumentKind.TOOLS, None),
    SIGNIFICANCE_PERCEPTION_MD_REL: (
        CompanionMemoryDocumentKind.SIGNIFICANCE_PERCEPTION,
        None,
    ),
    TRANSCRIPT_JSONL_REL: (CompanionMemoryDocumentKind.TRANSCRIPT, None),
    # TODO(rename-memory-doc): transcript_inner_tick_monolog.jsonl (with scope path + migration). — #3400
    TRANSCRIPT_INNER_TICK_JSONL_REL: (
        CompanionMemoryDocumentKind.TRANSCRIPT_INNER_TICK,
        None,
    ),
    CONTEXT_JSON_REL: (CompanionMemoryDocumentKind.CONTEXT_JSON, None),
    # TODO(rename-memory-doc): Rename ai_private.md to AI_PRIVATE.md (with migration). — #3400
    AI_PRIVATE_MD_REL: (CompanionMemoryDocumentKind.AI_PRIVATE_MD, None),
    # Inner thoughts about the user (MONOLOG)—not LIFE_CURRENTS virtual-world activity.
    # TODO(ai-private-jsonl-write): append-only write; not in write allowlist today (#3375, #3341).
    AI_PRIVATE_JSONL_REL: (CompanionMemoryDocumentKind.AI_PRIVATE_JSONL, None),
    TOOL_BACKGROUND_JSONL_REL: (
        CompanionMemoryDocumentKind.TOOL_BACKGROUND_JSONL,
        None,
    ),
    GENERATED_IMAGES_INDEX_JSONL_REL: (
        CompanionMemoryDocumentKind.GENERATED_IMAGES_INDEX_JSONL,
        None,
    ),
    COMPANION_LIVING_SPHERE_CURATOR_JSON_REL: (
        CompanionMemoryDocumentKind.COMPANION_LIVING_SPHERE_CURATOR_JSON,
        None,
    ),
    COMPANION_CONTEXT_COMPACTION_STATE_JSON_REL: (
        CompanionMemoryDocumentKind.COMPANION_CONTEXT_COMPACTION_STATE_JSON,
        None,
    ),
    COMPANION_SCHEDULE_TASKS_JSON_REL: (
        CompanionMemoryDocumentKind.COMPANION_SCHEDULE_TASKS_JSON,
        None,
    ),
    COMPANION_RUNTIME_EVENTS_JSONL_REL: (
        CompanionMemoryDocumentKind.COMPANION_RUNTIME_EVENTS_JSONL,
        None,
    ),
    COMPANION_USER_FEEDBACK_JSONL_REL: (
        CompanionMemoryDocumentKind.COMPANION_USER_FEEDBACK_JSONL,
        None,
    ),
    COMPANION_DREAMING_STATE_JSON_REL: (
        CompanionMemoryDocumentKind.COMPANION_DREAMING_STATE_JSON,
        None,
    ),
    INTY_V2_LIVING_SPHERE_CURATOR_JSON_REL: (
        CompanionMemoryDocumentKind.INTY_V2_LIVING_SPHERE_CURATOR_JSON,
        None,
    ),
    INTY_V2_CONTEXT_COMPACTION_STATE_JSON_REL: (
        CompanionMemoryDocumentKind.INTY_V2_CONTEXT_COMPACTION_STATE_JSON,
        None,
    ),
    INTY_V2_SCHEDULE_TASKS_JSON_REL: (
        CompanionMemoryDocumentKind.INTY_V2_SCHEDULE_TASKS_JSON,
        None,
    ),
}


def parse_memory_store_relative_path(
    relative_path: str,
) -> tuple[CompanionMemoryDocumentKind, date | None]:
    rel = (relative_path or "").strip().replace("\\", "/")
    if not rel:
        raise ValueError("relative_path must be non-empty")
    if rel in _REL_TO_KIND:
        return _REL_TO_KIND[rel]
    m_daily = _MEMORY_DAILY_RE.match(rel)
    if m_daily:
        d = date.fromisoformat(m_daily.group(1))
        return (CompanionMemoryDocumentKind.MEMORY_DAILY_RAW, d)
    raise ValueError(f"unsupported memory store document path for ORM: {rel!r}")


def relative_path_for_kind(
    kind: CompanionMemoryDocumentKind, calendar_date: date | None
) -> str:
    if kind == CompanionMemoryDocumentKind.MEMORY_DAILY_RAW:
        if calendar_date is None:
            raise ValueError(f"calendar_date required for {kind}")
        return f"memory/daily/{calendar_date.isoformat()}.md"
    if calendar_date is not None:
        raise ValueError(f"calendar_date must be null for {kind}")
    for rel, (k, cd) in _REL_TO_KIND.items():
        if k == kind and cd is None:
            return rel
    raise ValueError(f"no relative path mapping for {kind}")
