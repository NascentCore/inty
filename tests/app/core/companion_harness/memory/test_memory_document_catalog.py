from __future__ import annotations

import datetime

import pytest
from pathlib import Path

from app.core.companion_harness.memory.memory_document_catalog import (
    MEMORY_DAILY_GIST_ENTRY,
    MEMORY_DAILY_RELATIVE_PATH_TEMPLATE,
    MEMORY_DOCUMENT_CATALOG,
    MemoryDocumentWriter,
    MemoryInjectionSlot,
    catalog_bundle_field_paths,
    catalog_static_rel_to_kind,
    catalog_tool_writable_paths,
    memory_daily_relative_path,
    memory_injection_heading,
)
from app.core.companion_harness.tools.companion_tool_definitions import (
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST,
)
from app.core.companion_harness.companion.models import ContextMeta, load_prompt_bundle
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.utc import local_date_str
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
    ensure_minimal_documents_in_store,
)
from app.core.companion_harness.memory.memory_store_document_mapping import (
    parse_memory_store_relative_path,
    relative_path_for_kind,
)
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
    MemoryStoreScopePaths,
)
from app.core.companion_harness.memory.memory_taxonomy import (
    MEMORY_SYSTEM_HEADING_DAILY_GIST,
    MEMORY_SYSTEM_HEADING_SEMANTIC,
)
from app.core.companion_harness.prompting.bundle import PromptBundle


def test_catalog_static_paths_roundtrip() -> None:
    for rel in catalog_static_rel_to_kind():
        kind, cal = parse_memory_store_relative_path(rel)
        assert relative_path_for_kind(kind, cal) == rel


def test_catalog_daily_gist_roundtrip() -> None:
    rel = memory_daily_relative_path("2026-03-01")
    kind, cal = parse_memory_store_relative_path(rel)
    assert kind == MEMORY_DAILY_GIST_ENTRY.document_kind
    assert cal == datetime.date(2026, 3, 1)
    assert relative_path_for_kind(kind, cal) == rel


def test_catalog_bundle_fields_exist_on_prompt_bundle() -> None:
    model_fields = PromptBundle.model_fields
    for field_name in catalog_bundle_field_paths():
        assert field_name in model_fields, field_name


def test_catalog_scope_paths_match_static_entries() -> None:
    paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    for entry in MEMORY_DOCUMENT_CATALOG:
        if entry.scope_attr is None or entry.state_prefix is not None:
            continue
        assert getattr(paths, entry.scope_attr) == entry.relative_path


def test_catalog_scope_daily_gist_matches_template() -> None:
    paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    day = "2026-04-05"
    assert paths.memory_daily_gist(day) == MEMORY_DAILY_RELATIVE_PATH_TEMPLATE.format(
        date=day
    )


def test_catalog_injection_headings_reference_catalog_paths() -> None:
    assert MEMORY_DAILY_RELATIVE_PATH_TEMPLATE.replace("{date}", "{date}") in (
        memory_injection_heading(MemoryInjectionSlot.MEMORY_DAILY_GIST)
    )
    assert "MEMORY.md" in memory_injection_heading(MemoryInjectionSlot.MEMORY_SEMANTIC)
    assert MEMORY_SYSTEM_HEADING_DAILY_GIST == memory_injection_heading(
        MemoryInjectionSlot.MEMORY_DAILY_GIST
    )
    assert MEMORY_SYSTEM_HEADING_SEMANTIC == memory_injection_heading(
        MemoryInjectionSlot.MEMORY_SEMANTIC
    )


def test_catalog_daily_gist_entry_links_all_four_surfaces() -> None:
    entry = MEMORY_DAILY_GIST_ENTRY
    paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    assert entry.bundle_field == "memory_daily_today_md"
    assert entry.injection_slot == MemoryInjectionSlot.MEMORY_DAILY_GIST
    assert paths.memory_daily_gist("2099-01-01") == "memory/daily/2099-01-01.md"
    kind, _ = parse_memory_store_relative_path("memory/daily/2099-01-01.md")
    assert kind == entry.document_kind
    assert "memory_daily_today_md" in PromptBundle.model_fields


def test_catalog_state_prefix_scope_paths() -> None:
    companion = MemoryStoreScopePaths(state_file_prefix=".companion")
    inty_v2 = MemoryStoreScopePaths(state_file_prefix=".inty_v2")
    assert companion.dreaming_state_json == ".companion_dreaming_state.json"
    assert inty_v2.dreaming_state_json == ".inty_v2_dreaming_state.json"
    assert inty_v2.schedule_queue_json == ".inty_v2_schedule_tasks.json"


def test_invalid_path_raises() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        parse_memory_store_relative_path("memory/not-a-date.md")


def test_catalog_tool_writable_paths_match_allowlist() -> None:
    assert catalog_tool_writable_paths() == MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST


def test_memory_daily_gist_writer_is_dreaming_not_tool_writable() -> None:
    assert MEMORY_DAILY_GIST_ENTRY.writer == MemoryDocumentWriter.DREAMING
    assert not MEMORY_DAILY_GIST_ENTRY.tool_writable
    assert MEMORY_DAILY_RELATIVE_PATH_TEMPLATE.format(date="2099-01-01") not in (
        MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST
    )


def test_load_prompt_bundle_populates_catalog_linked_fields(tmp_path: Path) -> None:
    root = tmp_path / "bundle-load"
    root.mkdir()
    store = MemoryStore(
        scope=CompanionScope("catalog", "a", str(root.resolve())),
        repository=None,
    )
    ensure_minimal_documents_in_store(store)
    store.write_document("TECHNO_CORE.md", "techno-core-body\n")
    store.write_document("LIVING_SPHERE.md", "living-sphere-body\n")
    day = local_date_str()
    store.write_document(
        DEFAULT_MEMORY_STORE_SCOPE_PATHS.memory_daily_gist(day),
        "daily-gist-body\n",
    )

    bundle = load_prompt_bundle(store, meta=ContextMeta(context_mode="intimate"))
    for field_name in catalog_bundle_field_paths():
        value = getattr(bundle, field_name)
        assert isinstance(value, str)
        if field_name in {
            "identity",
            "soul",
            "style_md",
            "user_md",
            "memory_md",
            "channels_md",
            "tools_md",
            "significance_perception_md",
        }:
            assert value.strip()

    assert bundle.output_format_wechat_weixin_md.strip()
