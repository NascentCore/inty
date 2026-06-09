"""Cross-check MemoryDocumentCatalog against scope, ORM mapping, and PromptBundle."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from app.core.companion_harness.memory.document_catalog import (
    MEMORY_DOCUMENT_CATALOG,
    catalog_entry_for_path,
    catalog_paths_for_prompt_bundle_fields,
    memory_daily_catalog_entry,
    scope_path_for_attr,
)
from app.core.companion_harness.memory.memory_store_document_mapping import (
    all_static_relative_paths,
    parse_memory_store_relative_path,
    relative_path_for_kind,
)
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)
from app.core.companion_harness.system_hierarchy.bundle import PromptBundle


def test_catalog_static_paths_match_document_mapping() -> None:
    catalog_paths = {e.path for e in MEMORY_DOCUMENT_CATALOG}
    mapping_paths = all_static_relative_paths()
    # Package-seed OUTPUT_FORMAT is catalog-only (no ORM row).
    orm_backed = {
        e.path for e in MEMORY_DOCUMENT_CATALOG if e.document_kind is not None
    }
    assert orm_backed <= mapping_paths
    for path in orm_backed:
        entry = catalog_entry_for_path(path)
        assert entry is not None
        assert entry.document_kind is not None
        kind, _ = parse_memory_store_relative_path(path)
        assert entry.document_kind == kind


def test_catalog_scope_attrs_match_memory_store_scope_paths() -> None:
    paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    for entry in MEMORY_DOCUMENT_CATALOG:
        if entry.scope_paths_attr is None:
            continue
        assert scope_path_for_attr(paths, entry.scope_paths_attr) == entry.path


def test_memory_daily_catalog_matches_scope_and_mapping() -> None:
    day = "2026-06-09"
    entry = memory_daily_catalog_entry(day)
    assert (
        entry.path
        == DEFAULT_MEMORY_STORE_SCOPE_PATHS.memory_daily_gist(day)
    )
    kind, cal = parse_memory_store_relative_path(entry.path)
    assert kind == entry.document_kind
    assert cal == date.fromisoformat(day)
    assert (
        relative_path_for_kind(entry.document_kind, cal) == entry.path
    )


def test_prompt_bundle_fields_covered_by_catalog() -> None:
    bundle_fields = set(PromptBundle.model_fields.keys())
    catalog_fields = set(catalog_paths_for_prompt_bundle_fields().keys())
    assert catalog_fields == bundle_fields


def test_catalog_entry_lookup_roundtrip() -> None:
    for entry in MEMORY_DOCUMENT_CATALOG:
        assert catalog_entry_for_path(entry.path) == entry


class _FieldTypes(BaseModel):
    """Mirror PromptBundle field names for type sanity only."""

    identity: str
    soul: str
    style_md: str
    user_md: str
    memory_md: str
    techno_core_md: str
    living_sphere_md: str
    significance_perception_md: str
    channels_md: str
    output_format_wechat_weixin_md: str
    tools_md: str
    memory_daily_today_md: str


def test_catalog_bundle_field_names_exist_on_prompt_bundle() -> None:
    for entry in MEMORY_DOCUMENT_CATALOG:
        if entry.prompt_bundle_field is None:
            continue
        assert entry.prompt_bundle_field in PromptBundle.model_fields
