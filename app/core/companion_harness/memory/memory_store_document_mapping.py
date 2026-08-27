"""Map logical document paths (scope-relative) to ORM (document_kind, calendar_date)."""

from __future__ import annotations

import re
from datetime import date
from enum import Enum
from typing import Final

from .memory_store_path_constants import (
    MEMORY_DAILY_GIST_DIR_REL,
    memory_daily_gist_rel,
)

_MEMORY_DAILY_RE: Final[re.Pattern[str]] = re.compile(
    rf"^{re.escape(MEMORY_DAILY_GIST_DIR_REL)}/(\d{{4}}-\d{{2}}-\d{{2}})\.md$",
    re.IGNORECASE,
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
    # Capability slices from MemoryStore, not _template_doc_truncated. #3506
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
    INTY_V2_DREAMING_STATE_JSON = "inty_v2_dreaming_state_json"


_REL_TO_KIND: dict[str, tuple[CompanionMemoryDocumentKind, date | None]] | None = (
    None
)


def _rel_to_kind_map() -> dict[str, tuple[CompanionMemoryDocumentKind, date | None]]:
    """Lazily build ORM path map from scope accessors (avoids import cycle with memory_store_scope)."""
    global _REL_TO_KIND
    if _REL_TO_KIND is not None:
        return _REL_TO_KIND
    from .memory_store_scope import DEFAULT_MEMORY_STORE_SCOPE_PATHS, MemoryStoreScopePaths

    companion_paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    inty_v2_paths = MemoryStoreScopePaths(state_file_prefix=".inty_v2")
    _REL_TO_KIND = {
        companion_paths.identity: (CompanionMemoryDocumentKind.IDENTITY, None),
        companion_paths.soul: (CompanionMemoryDocumentKind.SOUL, None),
        companion_paths.style_md: (CompanionMemoryDocumentKind.STYLE, None),
        companion_paths.user_md: (CompanionMemoryDocumentKind.USER, None),
        companion_paths.memory_md: (CompanionMemoryDocumentKind.MEMORY, None),
        # Virtual-space activity state (AUTONOMY): what Inty is doing in the world—not inner thoughts about the user.
        companion_paths.life_currents_md: (
            CompanionMemoryDocumentKind.LIFE_CURRENTS,
            None,
        ),
        companion_paths.channels_md: (CompanionMemoryDocumentKind.CHANNELS, None),
        companion_paths.companionship_md: (
            CompanionMemoryDocumentKind.COMPANIONSHIP,
            None,
        ),
        companion_paths.techno_core_md: (
            CompanionMemoryDocumentKind.TECHNO_CORE,
            None,
        ),
        companion_paths.techno_core_events_jsonl: (
            CompanionMemoryDocumentKind.TECHNO_CORE_EVENTS_JSONL,
            None,
        ),
        companion_paths.living_sphere_md: (
            CompanionMemoryDocumentKind.LIVING_SPHERE,
            None,
        ),
        companion_paths.living_sphere_updates_jsonl: (
            CompanionMemoryDocumentKind.LIVING_SPHERE_UPDATES_JSONL,
            None,
        ),
        companion_paths.tools_md: (CompanionMemoryDocumentKind.TOOLS, None),
        companion_paths.significance_perception_md: (
            CompanionMemoryDocumentKind.SIGNIFICANCE_PERCEPTION,
            None,
        ),
        companion_paths.transcript: (CompanionMemoryDocumentKind.TRANSCRIPT, None),
        # TODO(rename-memory-doc): transcript_inner_tick_monolog.jsonl (with scope path + migration). — #3817
        companion_paths.transcript_inner_tick: (
            CompanionMemoryDocumentKind.TRANSCRIPT_INNER_TICK,
            None,
        ),
        companion_paths.context_json: (
            CompanionMemoryDocumentKind.CONTEXT_JSON,
            None,
        ),
        # TODO(rename-memory-doc): Rename ai_private.md to AI_PRIVATE.md (with migration). — #3817
        companion_paths.ai_private_md: (
            CompanionMemoryDocumentKind.AI_PRIVATE_MD,
            None,
        ),
        # Inner thoughts about the user (MONOLOG)—not LIFE_CURRENTS virtual-world activity.
        # TODO(ai-private-jsonl-write): append-only write; not in write allowlist today (#3375, #3341).
        companion_paths.ai_private_jsonl: (
            CompanionMemoryDocumentKind.AI_PRIVATE_JSONL,
            None,
        ),
        companion_paths.tool_background_jsonl: (
            CompanionMemoryDocumentKind.TOOL_BACKGROUND_JSONL,
            None,
        ),
        companion_paths.generated_images_index_jsonl: (
            CompanionMemoryDocumentKind.GENERATED_IMAGES_INDEX_JSONL,
            None,
        ),
        companion_paths.living_sphere_curator_state_json: (
            CompanionMemoryDocumentKind.COMPANION_LIVING_SPHERE_CURATOR_JSON,
            None,
        ),
        companion_paths.context_compaction_state_json: (
            CompanionMemoryDocumentKind.COMPANION_CONTEXT_COMPACTION_STATE_JSON,
            None,
        ),
        companion_paths.schedule_queue_json: (
            CompanionMemoryDocumentKind.COMPANION_SCHEDULE_TASKS_JSON,
            None,
        ),
        companion_paths.companion_runtime_events_jsonl: (
            CompanionMemoryDocumentKind.COMPANION_RUNTIME_EVENTS_JSONL,
            None,
        ),
        companion_paths.companion_user_feedback_jsonl: (
            CompanionMemoryDocumentKind.COMPANION_USER_FEEDBACK_JSONL,
            None,
        ),
        companion_paths.dreaming_state_json: (
            CompanionMemoryDocumentKind.COMPANION_DREAMING_STATE_JSON,
            None,
        ),
        inty_v2_paths.living_sphere_curator_state_json: (
            CompanionMemoryDocumentKind.INTY_V2_LIVING_SPHERE_CURATOR_JSON,
            None,
        ),
        inty_v2_paths.context_compaction_state_json: (
            CompanionMemoryDocumentKind.INTY_V2_CONTEXT_COMPACTION_STATE_JSON,
            None,
        ),
        inty_v2_paths.schedule_queue_json: (
            CompanionMemoryDocumentKind.INTY_V2_SCHEDULE_TASKS_JSON,
            None,
        ),
        inty_v2_paths.dreaming_state_json: (
            CompanionMemoryDocumentKind.INTY_V2_DREAMING_STATE_JSON,
            None,
        ),
    }
    return _REL_TO_KIND


def parse_memory_store_relative_path(
    relative_path: str,
) -> tuple[CompanionMemoryDocumentKind, date | None]:
    rel = (relative_path or "").strip().replace("\\", "/")
    if not rel:
        raise ValueError("relative_path must be non-empty")
    rel_to_kind = _rel_to_kind_map()
    if rel in rel_to_kind:
        return rel_to_kind[rel]
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
        return memory_daily_gist_rel(calendar_date.isoformat())
    if calendar_date is not None:
        raise ValueError(f"calendar_date must be null for {kind}")
    for rel, (k, cd) in _rel_to_kind_map().items():
        if k == kind and cd is None:
            return rel
    raise ValueError(f"no relative path mapping for {kind}")
