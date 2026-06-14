"""Map logical document paths (scope-relative) to ORM (document_kind, calendar_date)."""

from __future__ import annotations

import re
from datetime import date
from enum import Enum
from typing import Final

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
    TECHNO_CORE = "techno_core"
    TECHNO_CORE_EVENTS_JSONL = "techno_core_events_jsonl"
    LIVING_SPHERE = "living_sphere"
    LIVING_SPHERE_UPDATES_JSONL = "living_sphere_updates_jsonl"
    TOOLS = "tools"
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


# TODO(memdoc-path-constants): Derive keys from canonical MemDoc path constants (shared with
# MemoryStoreScopePaths) instead of duplicating literals. #3413
_REL_TO_KIND: dict[str, tuple[CompanionMemoryDocumentKind, date | None]] = {
    "IDENTITY.md": (CompanionMemoryDocumentKind.IDENTITY, None),
    "SOUL.md": (CompanionMemoryDocumentKind.SOUL, None),
    "STYLE.md": (CompanionMemoryDocumentKind.STYLE, None),
    "USER.md": (CompanionMemoryDocumentKind.USER, None),
    "MEMORY.md": (CompanionMemoryDocumentKind.MEMORY, None),
    # Virtual-space activity state (AUTONOMY): what Inty is doing in the world—not inner thoughts about the user.
    "LIFE_CURRENTS.md": (CompanionMemoryDocumentKind.LIFE_CURRENTS, None),
    "CHANNELS.md": (CompanionMemoryDocumentKind.CHANNELS, None),
    "TECHNO_CORE.md": (CompanionMemoryDocumentKind.TECHNO_CORE, None),
    "techno_core_events.jsonl": (
        CompanionMemoryDocumentKind.TECHNO_CORE_EVENTS_JSONL,
        None,
    ),
    "LIVING_SPHERE.md": (CompanionMemoryDocumentKind.LIVING_SPHERE, None),
    "living_sphere_updates.jsonl": (
        CompanionMemoryDocumentKind.LIVING_SPHERE_UPDATES_JSONL,
        None,
    ),
    "TOOLS.md": (CompanionMemoryDocumentKind.TOOLS, None),
    "SIGNIFICANCE_PERCEPTION.md": (
        CompanionMemoryDocumentKind.SIGNIFICANCE_PERCEPTION,
        None,
    ),
    "transcript.jsonl": (CompanionMemoryDocumentKind.TRANSCRIPT, None),
    # TODO(rename-memory-doc): transcript_inner_tick_maintenance.jsonl (with scope path + migration).
    "transcript_inner_tick.jsonl": (
        CompanionMemoryDocumentKind.TRANSCRIPT_INNER_TICK,
        None,
    ),
    "context.json": (CompanionMemoryDocumentKind.CONTEXT_JSON, None),
    "ai_private.md": (CompanionMemoryDocumentKind.AI_PRIVATE_MD, None),
    # Inner thoughts about the user (MAINTENANCE)—not LIFE_CURRENTS virtual-world activity.
    # TODO(ai-private-jsonl-write): append-only write; not in write allowlist today (#3375, #3341).
    # TODO(crs-companionship-doc): add ``COMPANIONSHIP`` document_kind when Phase A lands (#3342).
    "ai_private.jsonl": (CompanionMemoryDocumentKind.AI_PRIVATE_JSONL, None),
    "tool_background.jsonl": (
        CompanionMemoryDocumentKind.TOOL_BACKGROUND_JSONL,
        None,
    ),
    "generated_images/index.jsonl": (
        CompanionMemoryDocumentKind.GENERATED_IMAGES_INDEX_JSONL,
        None,
    ),
    ".companion_living_sphere_curator.json": (
        CompanionMemoryDocumentKind.COMPANION_LIVING_SPHERE_CURATOR_JSON,
        None,
    ),
    ".companion_context_compaction_state.json": (
        CompanionMemoryDocumentKind.COMPANION_CONTEXT_COMPACTION_STATE_JSON,
        None,
    ),
    ".companion_schedule_tasks.json": (
        CompanionMemoryDocumentKind.COMPANION_SCHEDULE_TASKS_JSON,
        None,
    ),
    ".companion_runtime_events.jsonl": (
        CompanionMemoryDocumentKind.COMPANION_RUNTIME_EVENTS_JSONL,
        None,
    ),
    ".companion_user_feedback.jsonl": (
        CompanionMemoryDocumentKind.COMPANION_USER_FEEDBACK_JSONL,
        None,
    ),
    ".companion_dreaming_state.json": (
        CompanionMemoryDocumentKind.COMPANION_DREAMING_STATE_JSON,
        None,
    ),
    ".inty_v2_living_sphere_curator.json": (
        CompanionMemoryDocumentKind.INTY_V2_LIVING_SPHERE_CURATOR_JSON,
        None,
    ),
    ".inty_v2_context_compaction_state.json": (
        CompanionMemoryDocumentKind.INTY_V2_CONTEXT_COMPACTION_STATE_JSON,
        None,
    ),
    ".inty_v2_schedule_tasks.json": (
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


def all_static_relative_paths() -> frozenset[str]:
    return frozenset(_REL_TO_KIND.keys())
