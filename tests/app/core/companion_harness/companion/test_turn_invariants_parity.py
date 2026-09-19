"""Cross-module parity between turn_invariants and lifecycle_invariants."""

from __future__ import annotations

import ast
from pathlib import Path

from app.core.companion_harness.companion import lifecycle_invariants as lifecycle
from app.core.companion_harness.companion.turn_invariants import (
    DREAMING_BATCH_CURATION_ENTRY,
    FORBIDDEN_LEGACY_MEMORY_SYMBOLS,
)

_REPO_ROOT = Path(__file__).resolve().parents[5]
_HARNESS_ROOT = _REPO_ROOT / "app" / "core" / "companion_harness"


def test_dreaming_curation_entry_matches_lifecycle_invariants() -> None:
    assert DREAMING_BATCH_CURATION_ENTRY == lifecycle.DREAMING_MEMORY_CURATION_ENTRY


def _production_harness_py_files() -> list[Path]:
    out: list[Path] = []
    for path in _HARNESS_ROOT.rglob("*.py"):
        rel = path.relative_to(_REPO_ROOT).as_posix()
        if rel.startswith("tests/"):
            continue
        out.append(path)
    return out


def _forbidden_name_hits(tree: ast.AST, forbidden: frozenset[str]) -> list[str]:
    hits: list[str] = []
    for node in ast.walk(tree):
        match node:
            case ast.Name(id=name) if name in forbidden:
                hits.append(name)
            case ast.Attribute(attr=name) if name in forbidden:
                hits.append(name)
    return hits


def test_forbidden_legacy_memory_symbols_absent_from_production_harness() -> None:
    violations: list[str] = []
    for path in _production_harness_py_files():
        rel = path.relative_to(_REPO_ROOT).as_posix()
        if rel.endswith("turn_invariants.py"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        hits = sorted(set(_forbidden_name_hits(tree, FORBIDDEN_LEGACY_MEMORY_SYMBOLS)))
        if hits:
            violations.append(f"{rel}: {hits}")
    assert violations == []
