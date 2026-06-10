"""Single catalog for MemoryStore documents: path, ORM kind, PromptBundle field, injection slot, writer.

Add or remove a MemoryDoc by editing ``MEMORY_DOCUMENT_CATALOG`` (and ``MEMORY_DAILY_GIST_ENTRY`` for
date-parametric daily gist). ``memory_store_document_mapping``, ``memory_store_scope``,
``memory_taxonomy``, ``MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST``, and consistency tests derive from here.
System message assembly (``system_messages.py``) is **not** catalog-driven.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from enum import Enum, StrEnum
from typing import Final

MEMORY_DAILY_RELATIVE_PATH_TEMPLATE: Final[str] = "memory/daily/{date}.md"
MEMORY_DAILY_RELATIVE_PATH_RE: Final[re.Pattern[str]] = re.compile(
    r"^memory/daily/(\d{4}-\d{2}-\d{2})\.md$", re.IGNORECASE
)
MEMORY_DIR_RELATIVE_PATH: Final[str] = "memory"
MEMORY_DAILY_DIR_RELATIVE_PATH: Final[str] = "memory/daily"


class CompanionMemoryDocumentKind(str, Enum):
    """Persisted document discriminator (no DB path columns)."""

    IDENTITY = "identity"
    SOUL = "soul"
    STYLE = "style"
    USER = "user"
    MEMORY = "memory"
    CHANNELS = "channels"
    TECHNO_CORE = "techno_core"
    TECHNO_CORE_EVENTS_JSONL = "techno_core_events_jsonl"
    LIVING_SPHERE = "living_sphere"
    LIVING_SPHERE_UPDATES_JSONL = "living_sphere_updates_jsonl"
    TOOLS = "tools"
    SIGNIFICANCE_PERCEPTION = "significance_perception"
    TRANSCRIPT = "transcript"
    TRANSCRIPT_INNER_TICK = "transcript_inner_tick"
    CONTEXT_JSON = "context_json"
    AI_PRIVATE_MD = "ai_private_md"
    AI_PRIVATE_JSONL = "ai_private_jsonl"
    TOOL_BACKGROUND_JSONL = "tool_background_jsonl"
    GENERATED_IMAGES_INDEX_JSONL = "generated_images_index_jsonl"
    MEMORY_DAILY_RAW = "memory_daily_raw"
    COMPANION_LIVING_SPHERE_CURATOR_JSON = "companion_living_sphere_curator_json"
    COMPANION_CONTEXT_COMPACTION_STATE_JSON = (
        "companion_context_compaction_state_json"
    )
    COMPANION_SCHEDULE_TASKS_JSON = "companion_schedule_tasks_json"
    COMPANION_RUNTIME_EVENTS_JSONL = "companion_runtime_events_jsonl"
    COMPANION_DREAMING_STATE_JSON = "companion_dreaming_state_json"
    INTY_V2_LIVING_SPHERE_CURATOR_JSON = "inty_v2_living_sphere_curator_json"
    INTY_V2_CONTEXT_COMPACTION_STATE_JSON = (
        "inty_v2_context_compaction_state_json"
    )
    INTY_V2_SCHEDULE_TASKS_JSON = "inty_v2_schedule_tasks_json"


class MemoryDocumentWriter(StrEnum):
    """Primary writer lane for the document body."""

    AWAKE = "awake"
    DREAMING = "dreaming"
    SEED = "seed"


class MemoryInjectionSlot(StrEnum):
    """System-prompt injection slot for taxonomy headings (private memory layers)."""

    MEMORY_DAILY_GIST = "memory_daily_gist"
    MEMORY_SEMANTIC = "memory_semantic"


_INJECTION_SLOT_HEADINGS: Final[dict[MemoryInjectionSlot, str]] = {
    MemoryInjectionSlot.MEMORY_DAILY_GIST: (
        "MEMORY — daily gist / 单日摘要（memory/daily/{date}.md）\n\n"
    ),
    MemoryInjectionSlot.MEMORY_SEMANTIC: (
        "MEMORY — semantic memory / 语义记忆（MEMORY.md）\n\n"
    ),
}


@dataclass(frozen=True)
class MemoryDocumentCatalogEntry:
    """One MemoryStore document registered in the catalog."""

    document_kind: CompanionMemoryDocumentKind
    relative_path: str
    scope_attr: str | None = None
    bundle_field: str | None = None
    injection_slot: MemoryInjectionSlot | None = None
    writer: MemoryDocumentWriter | None = None
    state_prefix: str | None = None
    tool_writable: bool = False


MEMORY_DOCUMENT_CATALOG: Final[tuple[MemoryDocumentCatalogEntry, ...]] = (
    MemoryDocumentCatalogEntry(
        document_kind=CompanionMemoryDocumentKind.IDENTITY,
        relative_path="IDENTITY.md",
        scope_attr="identity",
        bundle_field="identity",
        writer=MemoryDocumentWriter.SEED,
        tool_writable=True,
    ),
    MemoryDocumentCatalogEntry(
        document_kind=CompanionMemoryDocumentKind.SOUL,
        relative_path="SOUL.md",
        scope_attr="soul",
        bundle_field="soul",
        writer=MemoryDocumentWriter.SEED,
        tool_writable=True,
    ),
    MemoryDocumentCatalogEntry(
        document_kind=CompanionMemoryDocumentKind.STYLE,
        relative_path="STYLE.md",
        scope_attr="style_md",
        bundle_field="style_md",
        writer=MemoryDocumentWriter.SEED,
        tool_writable=True,
    ),
    MemoryDocumentCatalogEntry(
        document_kind=CompanionMemoryDocumentKind.USER,
        relative_path="USER.md",
        scope_attr="user_md",
        bundle_field="user_md",
        writer=MemoryDocumentWriter.SEED,
        tool_writable=True,
    ),
    MemoryDocumentCatalogEntry(
        document_kind=CompanionMemoryDocumentKind.MEMORY,
        relative_path="MEMORY.md",
        scope_attr="memory_md",
        bundle_field="memory_md",
        injection_slot=MemoryInjectionSlot.MEMORY_SEMANTIC,
        writer=MemoryDocumentWriter.DREAMING,
        tool_writable=True,
    ),
    MemoryDocumentCatalogEntry(
        document_kind=CompanionMemoryDocumentKind.CHANNELS,
        relative_path="CHANNELS.md",
        scope_attr="channels_md",
        bundle_field="channels_md",
        writer=MemoryDocumentWriter.SEED,
    ),
    MemoryDocumentCatalogEntry(
        document_kind=CompanionMemoryDocumentKind.TECHNO_CORE,
        relative_path="TECHNO_CORE.md",
        scope_attr="techno_core_md",
        bundle_field="techno_core_md",
        writer=MemoryDocumentWriter.SEED,
    ),
    MemoryDocumentCatalogEntry(
        document_kind=CompanionMemoryDocumentKind.TECHNO_CORE_EVENTS_JSONL,
        relative_path="techno_core_events.jsonl",
        writer=MemoryDocumentWriter.AWAKE,
    ),
    MemoryDocumentCatalogEntry(
        document_kind=CompanionMemoryDocumentKind.LIVING_SPHERE,
        relative_path="LIVING_SPHERE.md",
        scope_attr="living_sphere_md",
        bundle_field="living_sphere_md",
        writer=MemoryDocumentWriter.AWAKE,
    ),
    MemoryDocumentCatalogEntry(
        document_kind=CompanionMemoryDocumentKind.LIVING_SPHERE_UPDATES_JSONL,
        relative_path="living_sphere_updates.jsonl",
        writer=MemoryDocumentWriter.AWAKE,
    ),
    MemoryDocumentCatalogEntry(
        document_kind=CompanionMemoryDocumentKind.TOOLS,
        relative_path="TOOLS.md",
        scope_attr="tools_md",
        bundle_field="tools_md",
        writer=MemoryDocumentWriter.SEED,
    ),
    MemoryDocumentCatalogEntry(
        document_kind=CompanionMemoryDocumentKind.SIGNIFICANCE_PERCEPTION,
        relative_path="SIGNIFICANCE_PERCEPTION.md",
        scope_attr="significance_perception_md",
        bundle_field="significance_perception_md",
        writer=MemoryDocumentWriter.SEED,
    ),
    MemoryDocumentCatalogEntry(
        document_kind=CompanionMemoryDocumentKind.TRANSCRIPT,
        relative_path="transcript.jsonl",
        scope_attr="transcript",
        writer=MemoryDocumentWriter.AWAKE,
    ),
    MemoryDocumentCatalogEntry(
        document_kind=CompanionMemoryDocumentKind.TRANSCRIPT_INNER_TICK,
        relative_path="transcript_inner_tick.jsonl",
        scope_attr="transcript_inner_tick",
        writer=MemoryDocumentWriter.AWAKE,
    ),
    MemoryDocumentCatalogEntry(
        document_kind=CompanionMemoryDocumentKind.CONTEXT_JSON,
        relative_path="context.json",
        scope_attr="context_json",
        writer=MemoryDocumentWriter.SEED,
    ),
    MemoryDocumentCatalogEntry(
        document_kind=CompanionMemoryDocumentKind.AI_PRIVATE_MD,
        relative_path="ai_private.md",
        scope_attr="ai_private_md",
        writer=MemoryDocumentWriter.AWAKE,
    ),
    MemoryDocumentCatalogEntry(
        document_kind=CompanionMemoryDocumentKind.AI_PRIVATE_JSONL,
        relative_path="ai_private.jsonl",
        scope_attr="ai_private_jsonl",
        writer=MemoryDocumentWriter.AWAKE,
    ),
    MemoryDocumentCatalogEntry(
        document_kind=CompanionMemoryDocumentKind.TOOL_BACKGROUND_JSONL,
        relative_path="tool_background.jsonl",
        writer=MemoryDocumentWriter.AWAKE,
    ),
    MemoryDocumentCatalogEntry(
        document_kind=CompanionMemoryDocumentKind.GENERATED_IMAGES_INDEX_JSONL,
        relative_path="generated_images/index.jsonl",
        writer=MemoryDocumentWriter.AWAKE,
    ),
    MemoryDocumentCatalogEntry(
        document_kind=CompanionMemoryDocumentKind.COMPANION_LIVING_SPHERE_CURATOR_JSON,
        relative_path=".companion_living_sphere_curator.json",
        scope_attr="living_sphere_curator_state_json",
        state_prefix=".companion",
        writer=MemoryDocumentWriter.AWAKE,
    ),
    MemoryDocumentCatalogEntry(
        document_kind=CompanionMemoryDocumentKind.COMPANION_CONTEXT_COMPACTION_STATE_JSON,
        relative_path=".companion_context_compaction_state.json",
        scope_attr="context_compaction_state_json",
        state_prefix=".companion",
        writer=MemoryDocumentWriter.AWAKE,
    ),
    MemoryDocumentCatalogEntry(
        document_kind=CompanionMemoryDocumentKind.COMPANION_SCHEDULE_TASKS_JSON,
        relative_path=".companion_schedule_tasks.json",
        scope_attr="schedule_queue_json",
        state_prefix=".companion",
        writer=MemoryDocumentWriter.AWAKE,
    ),
    MemoryDocumentCatalogEntry(
        document_kind=CompanionMemoryDocumentKind.COMPANION_RUNTIME_EVENTS_JSONL,
        relative_path=".companion_runtime_events.jsonl",
        writer=MemoryDocumentWriter.AWAKE,
    ),
    MemoryDocumentCatalogEntry(
        document_kind=CompanionMemoryDocumentKind.COMPANION_DREAMING_STATE_JSON,
        relative_path=".companion_dreaming_state.json",
        scope_attr="dreaming_state_json",
        state_prefix=".companion",
        writer=MemoryDocumentWriter.DREAMING,
    ),
    MemoryDocumentCatalogEntry(
        document_kind=CompanionMemoryDocumentKind.INTY_V2_LIVING_SPHERE_CURATOR_JSON,
        relative_path=".inty_v2_living_sphere_curator.json",
        scope_attr="living_sphere_curator_state_json",
        state_prefix=".inty_v2",
        writer=MemoryDocumentWriter.AWAKE,
    ),
    MemoryDocumentCatalogEntry(
        document_kind=CompanionMemoryDocumentKind.INTY_V2_CONTEXT_COMPACTION_STATE_JSON,
        relative_path=".inty_v2_context_compaction_state.json",
        scope_attr="context_compaction_state_json",
        state_prefix=".inty_v2",
        writer=MemoryDocumentWriter.AWAKE,
    ),
    MemoryDocumentCatalogEntry(
        document_kind=CompanionMemoryDocumentKind.INTY_V2_SCHEDULE_TASKS_JSON,
        relative_path=".inty_v2_schedule_tasks.json",
        scope_attr="schedule_queue_json",
        state_prefix=".inty_v2",
        writer=MemoryDocumentWriter.AWAKE,
    ),
)

MEMORY_DAILY_GIST_ENTRY: Final[MemoryDocumentCatalogEntry] = MemoryDocumentCatalogEntry(
    document_kind=CompanionMemoryDocumentKind.MEMORY_DAILY_RAW,
    relative_path=MEMORY_DAILY_RELATIVE_PATH_TEMPLATE,
    scope_attr="memory_daily_gist",
    bundle_field="memory_daily_today_md",
    injection_slot=MemoryInjectionSlot.MEMORY_DAILY_GIST,
    writer=MemoryDocumentWriter.DREAMING,
)


def memory_injection_heading(slot: MemoryInjectionSlot) -> str:
    """Stable system-injection lead-in for a catalog injection slot."""
    return _INJECTION_SLOT_HEADINGS[slot]


def memory_daily_relative_path(day: str) -> str:
    """Scope-relative path for one calendar day's daily gist."""
    return MEMORY_DAILY_RELATIVE_PATH_TEMPLATE.format(date=day)


def catalog_static_rel_to_kind() -> dict[
    str, tuple[CompanionMemoryDocumentKind, date | None]
]:
    """Static path → (document_kind, calendar_date) derived from the catalog."""
    out: dict[str, tuple[CompanionMemoryDocumentKind, date | None]] = {}
    for entry in MEMORY_DOCUMENT_CATALOG:
        out[entry.relative_path] = (entry.document_kind, None)
    return out


def catalog_all_static_relative_paths() -> frozenset[str]:
    return frozenset(catalog_static_rel_to_kind())


def catalog_entry_for_scope_attr(
    scope_attr: str,
    *,
    state_prefix: str,
) -> MemoryDocumentCatalogEntry:
    """Resolve a ``MemoryStoreScopePaths`` accessor to its catalog row."""
    if scope_attr == MEMORY_DAILY_GIST_ENTRY.scope_attr:
        return MEMORY_DAILY_GIST_ENTRY
    matches = [
        entry
        for entry in MEMORY_DOCUMENT_CATALOG
        if entry.scope_attr == scope_attr
    ]
    if not matches:
        raise KeyError(f"no catalog entry for scope_attr={scope_attr!r}")
    for entry in matches:
        if entry.state_prefix == state_prefix:
            return entry
    for entry in matches:
        if entry.state_prefix is None:
            return entry
    # Prefixed template row (e.g. .companion_*); caller may swap prefix for .inty_v2_*.
    prefixed = [entry for entry in matches if entry.state_prefix is not None]
    if prefixed:
        return prefixed[0]
    raise KeyError(
        f"no catalog entry for scope_attr={scope_attr!r} state_prefix={state_prefix!r}"
    )


def scope_relative_path(
    scope_attr: str,
    *,
    state_prefix: str,
    day: str | None = None,
) -> str:
    """Scope-relative path for a catalog ``scope_attr`` (date required for daily gist)."""
    entry = catalog_entry_for_scope_attr(scope_attr, state_prefix=state_prefix)
    if entry is MEMORY_DAILY_GIST_ENTRY:
        assert day is not None
        return memory_daily_relative_path(day)
    if (
        entry.state_prefix is not None
        and entry.state_prefix != state_prefix
    ):
        suffix = entry.relative_path.removeprefix(entry.state_prefix)
        return f"{state_prefix}{suffix}"
    return entry.relative_path


def catalog_bundle_field_paths() -> dict[str, str]:
    """PromptBundle field name → static relative path (daily gist uses template)."""
    out: dict[str, str] = {}
    for entry in (*MEMORY_DOCUMENT_CATALOG, MEMORY_DAILY_GIST_ENTRY):
        if entry.bundle_field is not None:
            out[entry.bundle_field] = entry.relative_path
    return out


def catalog_tool_writable_paths() -> frozenset[str]:
    """Static relative paths ``memory_store_write_document`` may overwrite."""
    return frozenset(
        entry.relative_path
        for entry in (*MEMORY_DOCUMENT_CATALOG, MEMORY_DAILY_GIST_ENTRY)
        if entry.tool_writable
    )
