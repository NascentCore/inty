"""Architecture tests for AwakeTurn vs DreamingBatch memory lifecycle invariants."""

from __future__ import annotations

import ast

from app.core.companion_harness.companion import lifecycle_invariants as inv


def test_awake_turn_kernel_does_not_import_dreaming_consolidation() -> None:
    for rel in inv.AWAKE_TURN_SURFACE_MODULE_PATHS:
        hits = inv.module_source_contains_forbidden_import(
            rel,
            forbidden_substrings=inv.AWAKE_TURN_FORBIDDEN_IMPORT_SUBSTRINGS,
        )
        assert hits == [], f"{rel} forbidden imports: {hits}"


def test_awake_turn_surface_does_not_call_consolidate_memory_during_dreaming() -> None:
    for rel in inv.AWAKE_TURN_SURFACE_MODULE_PATHS:
        assert not inv.module_calls_named(
            rel, inv.DREAMING_MEMORY_CURATION_ENTRY
        ), f"{rel} must not call {inv.DREAMING_MEMORY_CURATION_ENTRY}"


def test_awake_turn_kernel_only_appends_transcript_jsonl() -> None:
    for rel in inv.AWAKE_TURN_KERNEL_MODULE_PATHS:
        write_lines = inv.module_calls_store_method(
            rel, "write_document"
        )
        assert write_lines == [], (
            f"{rel} must not call store.write_document "
            f"(lines {write_lines}); AwakeTurn kernel append-only"
        )
        literal_paths = inv.append_jsonl_literal_paths(rel)
        for path in literal_paths:
            assert path in inv.AWAKE_TURN_ALLOWED_APPEND_JSONL, (
                f"{rel} append_jsonl_record literal {path!r} not in "
                f"{sorted(inv.AWAKE_TURN_ALLOWED_APPEND_JSONL)}"
            )


def test_tool_background_log_append_is_tool_background_jsonl() -> None:
    rel = inv.AWAKE_TURN_TOOL_BACKGROUND_MODULE_PATH
    literal_paths = inv.append_jsonl_literal_paths(rel)
    assert inv.AWAKE_TURN_TOOL_BACKGROUND_LOG_JSONL in literal_paths
    assert not inv.module_calls_store_method(rel, "write_document")


def test_dreaming_batch_orchestrator_calls_consolidate_memory_during_dreaming() -> None:
    rel = inv.DREAMING_BATCH_ORCHESTRATOR_MODULE_PATH
    assert inv.function_body_calls_named(
        rel,
        inv.DREAMING_BATCH_ORCHESTRATOR_FUNCTION,
        inv.DREAMING_MEMORY_CURATION_ENTRY,
    )


def test_consolidate_memory_during_dreaming_only_referenced_from_allowlist() -> None:
    referencers = inv.app_py_files_importing_or_calling(
        inv.DREAMING_MEMORY_CURATION_ENTRY
    )
    unexpected = sorted(
        p
        for p in referencers
        if p not in inv.DREAMING_CONSOLIDATION_REFERENCE_ALLOWLIST
    )
    assert unexpected == [], (
        "consolidate_memory_during_dreaming referenced outside allowlist: "
        f"{unexpected}"
    )


def test_dreaming_memory_curation_defined_in_dreaming_consolidation_module() -> None:
    rel = inv.DREAMING_MEMORY_CURATION_MODULE_PATH
    tree = inv.parse_module_ast(rel)
    defs = [
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == inv.DREAMING_MEMORY_CURATION_ENTRY
    ]
    assert defs == [inv.DREAMING_MEMORY_CURATION_ENTRY]
