"""Map logical document paths (scope-relative) to ORM (document_kind, calendar_date)."""

from __future__ import annotations

from datetime import date

from .memory_document_catalog import (
    CompanionMemoryDocumentKind,
    MEMORY_DAILY_GIST_ENTRY,
    MEMORY_DAILY_RELATIVE_PATH_RE,
    catalog_all_static_relative_paths,
    catalog_static_rel_to_kind,
    memory_daily_relative_path,
)

__all__ = (
    "CompanionMemoryDocumentKind",
    "all_static_relative_paths",
    "parse_memory_store_relative_path",
    "relative_path_for_kind",
)

_REL_TO_KIND = catalog_static_rel_to_kind()


def parse_memory_store_relative_path(
    relative_path: str,
) -> tuple[CompanionMemoryDocumentKind, date | None]:
    rel = (relative_path or "").strip().replace("\\", "/")
    if not rel:
        raise ValueError("relative_path must be non-empty")
    if rel in _REL_TO_KIND:
        return _REL_TO_KIND[rel]
    m_daily = MEMORY_DAILY_RELATIVE_PATH_RE.match(rel)
    if m_daily:
        d = date.fromisoformat(m_daily.group(1))
        return (MEMORY_DAILY_GIST_ENTRY.document_kind, d)
    raise ValueError(f"unsupported memory store document path for ORM: {rel!r}")


def relative_path_for_kind(
    kind: CompanionMemoryDocumentKind, calendar_date: date | None
) -> str:
    if kind == MEMORY_DAILY_GIST_ENTRY.document_kind:
        if calendar_date is None:
            raise ValueError(f"calendar_date required for {kind}")
        return memory_daily_relative_path(calendar_date.isoformat())
    if calendar_date is not None:
        raise ValueError(f"calendar_date must be null for {kind}")
    for rel, (k, cd) in _REL_TO_KIND.items():
        if k == kind and cd is None:
            return rel
    raise ValueError(f"no relative path mapping for {kind}")


def all_static_relative_paths() -> frozenset[str]:
    return catalog_all_static_relative_paths()
