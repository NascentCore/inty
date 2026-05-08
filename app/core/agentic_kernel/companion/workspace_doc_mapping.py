"""Map workspace-relative paths to ORM (document_kind, calendar_date)."""

from __future__ import annotations

import re
from datetime import date
from enum import Enum
from typing import Final

_MEMORY_DAILY_RE: Final[re.Pattern[str]] = re.compile(
    r"^memory/daily/(\d{4}-\d{2}-\d{2})\.md$", re.IGNORECASE
)
_MEMORY_SUMMARY_RE: Final[re.Pattern[str]] = re.compile(
    r"^memory/(\d{4}-\d{2}-\d{2})\.md$", re.IGNORECASE
)


class CompanionWorkspaceDocKind(str, Enum):
    """Persisted document discriminator (no DB path columns)."""

    IDENTITY = "identity"
    SOUL = "soul"
    USER = "user"
    MEMORY = "memory"
    HEARTBEAT = "heartbeat"
    TOOLS = "tools"
    # Workspace seed SIGNIFICANCE_PERCEPTION.md; scoring semantics consumed via PromptBundle, not ORM-only.
    SIGNIFICANCE_PERCEPTION = "significance_perception"
    TRANSCRIPT = "transcript"
    CONTEXT_JSON = "context_json"
    AI_PRIVATE_MD = "ai_private_md"
    AI_PRIVATE_JSONL = "ai_private_jsonl"
    TOOL_BACKGROUND_JSONL = "tool_background_jsonl"
    GENERATED_IMAGES_INDEX_JSONL = "generated_images_index_jsonl"
    MEMORY_DAILY_RAW = "memory_daily_raw"  # episodic: memory/daily/<date>.md
    MEMORY_DAY_SUMMARY = "memory_day_summary"  # gist: memory/<date>.md
    COMPANION_MEMORY_PIPELINE_JSON = "companion_memory_pipeline_json"
    COMPANION_CONTEXT_COMPACTION_STATE_JSON = "companion_context_compaction_state_json"
    COMPANION_SCHEDULE_TASKS_JSON = "companion_schedule_tasks_json"
    COMPANION_IMAGE_GATE_JSON = "companion_image_gate_json"
    INTY_V2_MEMORY_PIPELINE_JSON = "inty_v2_memory_pipeline_json"
    INTY_V2_CONTEXT_COMPACTION_STATE_JSON = "inty_v2_context_compaction_state_json"
    INTY_V2_SCHEDULE_TASKS_JSON = "inty_v2_schedule_tasks_json"
    INTY_V2_IMAGE_GATE_JSON = "inty_v2_image_gate_json"


_REL_TO_KIND: dict[str, tuple[CompanionWorkspaceDocKind, date | None]] = {
    "IDENTITY.md": (CompanionWorkspaceDocKind.IDENTITY, None),
    "SOUL.md": (CompanionWorkspaceDocKind.SOUL, None),
    "USER.md": (CompanionWorkspaceDocKind.USER, None),
    "MEMORY.md": (CompanionWorkspaceDocKind.MEMORY, None),
    "HEARTBEAT.md": (CompanionWorkspaceDocKind.HEARTBEAT, None),
    "TOOLS.md": (CompanionWorkspaceDocKind.TOOLS, None),
    "SIGNIFICANCE_PERCEPTION.md": (
        CompanionWorkspaceDocKind.SIGNIFICANCE_PERCEPTION,
        None,
    ),
    "transcript.jsonl": (CompanionWorkspaceDocKind.TRANSCRIPT, None),
    "context.json": (CompanionWorkspaceDocKind.CONTEXT_JSON, None),
    "ai_private.md": (CompanionWorkspaceDocKind.AI_PRIVATE_MD, None),
    "ai_private.jsonl": (CompanionWorkspaceDocKind.AI_PRIVATE_JSONL, None),
    "tool_background.jsonl": (CompanionWorkspaceDocKind.TOOL_BACKGROUND_JSONL, None),
    "generated_images/index.jsonl": (
        CompanionWorkspaceDocKind.GENERATED_IMAGES_INDEX_JSONL,
        None,
    ),
    ".companion_memory_pipeline.json": (
        CompanionWorkspaceDocKind.COMPANION_MEMORY_PIPELINE_JSON,
        None,
    ),
    ".companion_context_compaction_state.json": (
        CompanionWorkspaceDocKind.COMPANION_CONTEXT_COMPACTION_STATE_JSON,
        None,
    ),
    ".companion_schedule_tasks.json": (
        CompanionWorkspaceDocKind.COMPANION_SCHEDULE_TASKS_JSON,
        None,
    ),
    ".companion_image_gate.json": (
        CompanionWorkspaceDocKind.COMPANION_IMAGE_GATE_JSON,
        None,
    ),
    ".inty_v2_memory_pipeline.json": (
        CompanionWorkspaceDocKind.INTY_V2_MEMORY_PIPELINE_JSON,
        None,
    ),
    ".inty_v2_context_compaction_state.json": (
        CompanionWorkspaceDocKind.INTY_V2_CONTEXT_COMPACTION_STATE_JSON,
        None,
    ),
    ".inty_v2_schedule_tasks.json": (
        CompanionWorkspaceDocKind.INTY_V2_SCHEDULE_TASKS_JSON,
        None,
    ),
    ".inty_v2_image_gate.json": (
        CompanionWorkspaceDocKind.INTY_V2_IMAGE_GATE_JSON,
        None,
    ),
}


def parse_workspace_relative_path(
    relative_path: str,
) -> tuple[CompanionWorkspaceDocKind, date | None]:
    rel = (relative_path or "").strip().replace("\\", "/")
    if not rel:
        raise ValueError("relative_path must be non-empty")
    if rel in _REL_TO_KIND:
        return _REL_TO_KIND[rel]
    m_daily = _MEMORY_DAILY_RE.match(rel)
    if m_daily:
        d = date.fromisoformat(m_daily.group(1))
        return (CompanionWorkspaceDocKind.MEMORY_DAILY_RAW, d)
    m_sum = _MEMORY_SUMMARY_RE.match(rel)
    if m_sum:
        d = date.fromisoformat(m_sum.group(1))
        return (CompanionWorkspaceDocKind.MEMORY_DAY_SUMMARY, d)
    raise ValueError(f"unsupported companion workspace path for ORM: {rel!r}")


def relative_path_for_kind(
    kind: CompanionWorkspaceDocKind, calendar_date: date | None
) -> str:
    if kind in (
        CompanionWorkspaceDocKind.MEMORY_DAILY_RAW,
        CompanionWorkspaceDocKind.MEMORY_DAY_SUMMARY,
    ):
        if calendar_date is None:
            raise ValueError(f"calendar_date required for {kind}")
        if kind == CompanionWorkspaceDocKind.MEMORY_DAILY_RAW:
            return f"memory/daily/{calendar_date.isoformat()}.md"
        return f"memory/{calendar_date.isoformat()}.md"
    if calendar_date is not None:
        raise ValueError(f"calendar_date must be null for {kind}")
    for rel, (k, cd) in _REL_TO_KIND.items():
        if k == kind and cd is None:
            return rel
    raise ValueError(f"no relative path mapping for {kind}")


def all_static_relative_paths() -> frozenset[str]:
    return frozenset(_REL_TO_KIND.keys())
