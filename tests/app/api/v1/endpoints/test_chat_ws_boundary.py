"""Architecture tests: companion WS surface must not depend on maintenance-mode agent stacks."""

from __future__ import annotations

from app.api.v1.endpoints import chat_ws_boundary as boundary


def test_companion_ws_surface_imports_companion_harness() -> None:
    for rel in boundary.CHAT_WS_BOUNDARY_MODULE_PATHS:
        assert boundary.module_imports_companion_harness(rel), (
            f"{rel} must import from {boundary.CHAT_WS_REQUIRED_APP_CORE_PREFIX}"
        )


def test_companion_ws_surface_does_not_import_maintenance_mode_modules() -> None:
    for rel in boundary.CHAT_WS_BOUNDARY_MODULE_PATHS:
        hits = boundary.module_imports_forbidden_maintenance_modules(rel)
        assert hits == [], f"{rel} forbidden imports: {hits}"


def test_companion_ws_surface_app_core_imports_are_allowlisted() -> None:
    for rel in boundary.CHAT_WS_BOUNDARY_MODULE_PATHS:
        hits = boundary.module_app_core_imports_outside_allowlist(rel)
        assert hits == [], f"{rel} disallowed app.core imports: {hits}"


def test_companion_production_surface_does_not_reference_readable_id() -> None:
    hits = boundary.companion_surface_readable_id_references()
    assert hits == [], (
        "companion_harness, agentic_channel, and /api/v1/chat/ws must not use "
        f"legacy readable_id; hits: {hits}"
    )


def test_ast_readable_id_references_detects_common_forms() -> None:
    source = """
x = obj.readable_id
y = readable_id
f(readable_id=1)
d = {"readable_id": 1}
z = row["readable_id"]
getattr(obj, "readable_id")
"""
    hits = boundary.ast_readable_id_references_in_source("probe.py", source)
    kinds = {hit.split(":")[-1] for hit in hits}
    assert kinds == {"name", "attribute", "keyword", "dict_key", "subscript", "getattr"}
