"""Architecture tests: agentic_companion must stay channel/API glue, not harness runtime."""

from __future__ import annotations

from app.services.agentic_companion import boundary


def test_agentic_companion_does_not_import_forbidden_harness_modules() -> None:
    for rel in boundary.agentic_companion_python_paths():
        hits = boundary.module_forbidden_harness_imports(rel)
        assert hits == [], f"{rel} forbidden harness imports: {hits}"


def test_agentic_companion_harness_imports_are_allowlisted() -> None:
    for rel in boundary.agentic_companion_python_paths():
        hits = boundary.module_disallowed_harness_imports(rel)
        assert hits == [], f"{rel} disallowed harness imports: {hits}"
