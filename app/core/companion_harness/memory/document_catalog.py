"""Single source of truth for MemoryStore document path metadata.

Generated entirely by Cursor agent for Phase 3 S7.

Maps scope-relative ``path`` ↔ ORM ``document_kind`` ↔ ``PromptBundle`` field ↔
``MemoryDocumentWriter``. Runtime behavior is unchanged; callers still use
``memory_store_scope`` and ``memory_store_document_mapping`` until a follow-up
slice wires catalog lookups into production paths.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from app.core.companion_harness.memory.memory_store_document_mapping import (
    CompanionMemoryDocumentKind,
    parse_memory_store_relative_path,
)
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
    MemoryStoreScopePaths,
)

_MEMORY_DAILY_PATH_RE: Final[re.Pattern[str]] = re.compile(
    r"^memory/daily/\d{4}-\d{2}-\d{2}\.md$"
)


class MemoryDocumentWriter(StrEnum):
    """Who may persist body content at this path."""

    AWAKE_APPEND = "awake_append"
    DREAMING_CURATION = "dreaming_curation"
    SEED = "seed"
    TOOL = "tool"


@dataclass(frozen=True)
class MemoryDocumentCatalogEntry:
    """One catalog row for a fixed scope-relative path."""

    path: str
    document_kind: CompanionMemoryDocumentKind | None
    writer: MemoryDocumentWriter
    prompt_bundle_field: str | None = None
    scope_paths_attr: str | None = None


def _row(
    path: str,
    *,
    kind: CompanionMemoryDocumentKind | None,
    writer: MemoryDocumentWriter,
    bundle_field: str | None = None,
    scope_attr: str | None = None,
) -> MemoryDocumentCatalogEntry:
    return MemoryDocumentCatalogEntry(
        path=path,
        document_kind=kind,
        writer=writer,
        prompt_bundle_field=bundle_field,
        scope_paths_attr=scope_attr,
    )


_PATHS = DEFAULT_MEMORY_STORE_SCOPE_PATHS

# Fixed paths only; ``memory/daily/<date>.md`` uses ``memory_daily_catalog_entry``.
MEMORY_DOCUMENT_CATALOG: tuple[MemoryDocumentCatalogEntry, ...] = (
    _row(
        _PATHS.identity,
        kind=CompanionMemoryDocumentKind.IDENTITY,
        writer=MemoryDocumentWriter.SEED,
        bundle_field="identity",
        scope_attr="identity",
    ),
    _row(
        _PATHS.soul,
        kind=CompanionMemoryDocumentKind.SOUL,
        writer=MemoryDocumentWriter.DREAMING_CURATION,
        bundle_field="soul",
        scope_attr="soul",
    ),
    _row(
        _PATHS.style_md,
        kind=CompanionMemoryDocumentKind.STYLE,
        writer=MemoryDocumentWriter.DREAMING_CURATION,
        bundle_field="style_md",
        scope_attr="style_md",
    ),
    _row(
        _PATHS.user_md,
        kind=CompanionMemoryDocumentKind.USER,
        writer=MemoryDocumentWriter.DREAMING_CURATION,
        bundle_field="user_md",
        scope_attr="user_md",
    ),
    _row(
        _PATHS.memory_md,
        kind=CompanionMemoryDocumentKind.MEMORY,
        writer=MemoryDocumentWriter.DREAMING_CURATION,
        bundle_field="memory_md",
        scope_attr="memory_md",
    ),
    _row(
        _PATHS.channels_md,
        kind=CompanionMemoryDocumentKind.CHANNELS,
        writer=MemoryDocumentWriter.SEED,
        bundle_field="channels_md",
        scope_attr="channels_md",
    ),
    _row(
        _PATHS.techno_core_md,
        kind=CompanionMemoryDocumentKind.TECHNO_CORE,
        writer=MemoryDocumentWriter.TOOL,
        bundle_field="techno_core_md",
        scope_attr="techno_core_md",
    ),
    _row(
        _PATHS.living_sphere_md,
        kind=CompanionMemoryDocumentKind.LIVING_SPHERE,
        writer=MemoryDocumentWriter.DREAMING_CURATION,
        bundle_field="living_sphere_md",
        scope_attr="living_sphere_md",
    ),
    _row(
        _PATHS.tools_md,
        kind=CompanionMemoryDocumentKind.TOOLS,
        writer=MemoryDocumentWriter.SEED,
        bundle_field="tools_md",
        scope_attr="tools_md",
    ),
    _row(
        _PATHS.significance_perception_md,
        kind=CompanionMemoryDocumentKind.SIGNIFICANCE_PERCEPTION,
        writer=MemoryDocumentWriter.SEED,
        bundle_field="significance_perception_md",
        scope_attr="significance_perception_md",
    ),
    _row(
        _PATHS.transcript,
        kind=CompanionMemoryDocumentKind.TRANSCRIPT,
        writer=MemoryDocumentWriter.AWAKE_APPEND,
        scope_attr="transcript",
    ),
    _row(
        _PATHS.transcript_inner_tick,
        kind=CompanionMemoryDocumentKind.TRANSCRIPT_INNER_TICK,
        writer=MemoryDocumentWriter.AWAKE_APPEND,
        scope_attr="transcript_inner_tick",
    ),
    _row(
        _PATHS.context_json,
        kind=CompanionMemoryDocumentKind.CONTEXT_JSON,
        writer=MemoryDocumentWriter.TOOL,
        scope_attr="context_json",
    ),
    _row(
        _PATHS.ai_private_md,
        kind=CompanionMemoryDocumentKind.AI_PRIVATE_MD,
        writer=MemoryDocumentWriter.TOOL,
        scope_attr="ai_private_md",
    ),
    _row(
        _PATHS.ai_private_jsonl,
        kind=CompanionMemoryDocumentKind.AI_PRIVATE_JSONL,
        writer=MemoryDocumentWriter.AWAKE_APPEND,
        scope_attr="ai_private_jsonl",
    ),
    _row(
        _PATHS.dreaming_state_json,
        kind=CompanionMemoryDocumentKind.COMPANION_DREAMING_STATE_JSON,
        writer=MemoryDocumentWriter.TOOL,
        scope_attr="dreaming_state_json",
    ),
    _row(
        _PATHS.schedule_queue_json,
        kind=CompanionMemoryDocumentKind.COMPANION_SCHEDULE_TASKS_JSON,
        writer=MemoryDocumentWriter.TOOL,
        scope_attr="schedule_queue_json",
    ),
    _row(
        _PATHS.living_sphere_curator_state_json,
        kind=CompanionMemoryDocumentKind.COMPANION_LIVING_SPHERE_CURATOR_JSON,
        writer=MemoryDocumentWriter.TOOL,
        scope_attr="living_sphere_curator_state_json",
    ),
    _row(
        _PATHS.context_compaction_state_json,
        kind=CompanionMemoryDocumentKind.COMPANION_CONTEXT_COMPACTION_STATE_JSON,
        writer=MemoryDocumentWriter.TOOL,
        scope_attr="context_compaction_state_json",
    ),
    MemoryDocumentCatalogEntry(
        path="OUTPUT_FORMAT_WECHAT_WEIXIN.md",
        document_kind=None,
        writer=MemoryDocumentWriter.SEED,
        prompt_bundle_field="output_format_wechat_weixin_md",
        scope_paths_attr=None,
    ),
)


def memory_daily_catalog_entry(day: str) -> MemoryDocumentCatalogEntry:
    """Catalog row for one ``memory/daily/<date>.md`` daily gist path."""
    assert day
    return MemoryDocumentCatalogEntry(
        path=_PATHS.memory_daily_gist(day),
        document_kind=CompanionMemoryDocumentKind.MEMORY_DAILY_RAW,
        writer=MemoryDocumentWriter.DREAMING_CURATION,
        prompt_bundle_field="memory_daily_today_md",
        scope_paths_attr=None,
    )


def catalog_entry_for_path(path: str) -> MemoryDocumentCatalogEntry | None:
    """Resolve a scope-relative path to a catalog row when known."""
    assert path
    for entry in MEMORY_DOCUMENT_CATALOG:
        if entry.path == path:
            return entry
    if _MEMORY_DAILY_PATH_RE.match(path):
        day = path.removeprefix("memory/daily/").removesuffix(".md")
        return memory_daily_catalog_entry(day)
    return None


def scope_path_for_attr(
    paths: MemoryStoreScopePaths,
    attr: str,
) -> str:
    """Read a ``MemoryStoreScopePaths`` property by attribute name."""
    assert attr
    return getattr(paths, attr)


def catalog_paths_for_prompt_bundle_fields() -> dict[str, str]:
    """``PromptBundle`` field name → primary scope-relative path."""
    out: dict[str, str] = {}
    for entry in MEMORY_DOCUMENT_CATALOG:
        if entry.prompt_bundle_field is not None:
            out[entry.prompt_bundle_field] = entry.path
    out["memory_daily_today_md"] = _PATHS.memory_daily_gist("YYYY-MM-DD")
    return out
