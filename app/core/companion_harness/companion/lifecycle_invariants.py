"""Companion memory lifecycle invariants: AwakeTurn vs DreamingBatch.

AwakeTurn kernel persists dialogue by appending transcript JSONL (and tool_background
append-only logs). DreamingBatch curates MemoryDocs only via consolidate_memory_during_dreaming.

Enforced by tests/app/core/companion_harness/companion/test_lifecycle_invariants.py.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Final

from app.core.companion_harness.memory import memory_store_path_constants as _memdoc_path_constants
from app.core.companion_harness.memory.memory_store_path_constants import (
    TOOL_BACKGROUND_JSONL_REL,
    TRANSCRIPT_INNER_TICK_JSONL_REL,
    TRANSCRIPT_JSONL_REL,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]

_MEMDOC_PATH_CONSTANT_NAMES: Final[frozenset[str]] = frozenset(
    name
    for name, value in vars(_memdoc_path_constants).items()
    if name.endswith("_REL") and isinstance(value, str)
)

# run_companion_*_turn → _run_companion_turn_core transcript persistence
AWAKE_TURN_KERNEL_MODULE_PATHS: Final[tuple[str, ...]] = (
    "app/core/companion_harness/companion/turn.py",
)

# Broader awake surface: must not invoke memory consolidation
AWAKE_TURN_SURFACE_MODULE_PATHS: Final[tuple[str, ...]] = (
    *AWAKE_TURN_KERNEL_MODULE_PATHS,
    "app/core/companion_harness/companion/turn_pipeline.py",
)

AWAKE_TURN_TOOL_BACKGROUND_MODULE_PATH: Final[str] = (
    "app/core/companion_harness/tools/tool_background.py"
)

AWAKE_TURN_ALLOWED_APPEND_JSONL: Final[frozenset[str]] = frozenset(
    {
        TRANSCRIPT_JSONL_REL,
        TRANSCRIPT_INNER_TICK_JSONL_REL,
    }
)

AWAKE_TURN_TOOL_BACKGROUND_LOG_JSONL: Final[str] = TOOL_BACKGROUND_JSONL_REL

AWAKE_TURN_FORBIDDEN_IMPORT_SUBSTRINGS: Final[frozenset[str]] = frozenset(
    {
        "dreaming_consolidation",
    }
)

DREAMING_BATCH_ORCHESTRATOR_MODULE_PATH: Final[str] = (
    "app/core/companion_harness/runtime/dreaming_batch.py"
)

DREAMING_MEMORY_CURATION_ENTRY: Final[str] = (
    "consolidate_memory_during_dreaming"
)

DREAMING_MEMORY_CURATION_MODULE_PATH: Final[str] = (
    "app/core/companion_harness/memory/dreaming_consolidation.py"
)

# Production app/ modules allowed to reference consolidate_memory_during_dreaming
DREAMING_CONSOLIDATION_REFERENCE_ALLOWLIST: Final[frozenset[str]] = frozenset(
    {
        DREAMING_BATCH_ORCHESTRATOR_MODULE_PATH,
        DREAMING_MEMORY_CURATION_MODULE_PATH,
    }
)


def repo_root() -> Path:
    return _REPO_ROOT


def module_absolute_path(relative_path: str) -> Path:
    return repo_root() / relative_path


def parse_module_ast(relative_path: str) -> ast.Module:
    source = module_absolute_path(relative_path).read_text(encoding="utf-8")
    return ast.parse(source, filename=relative_path)


def module_source_contains_forbidden_import(
    relative_path: str,
    *,
    forbidden_substrings: frozenset[str],
) -> list[str]:
    tree = parse_module_ast(relative_path)
    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Import):
            continue
        for alias in node.names:
            for sub in forbidden_substrings:
                if sub in alias.name:
                    hits.append(f"import {alias.name}")
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        mod = node.module or ""
        for sub in forbidden_substrings:
            if sub in mod:
                hits.append(f"from {mod} import ...")
    return hits


def module_calls_named(relative_path: str, name: str) -> bool:
    tree = parse_module_ast(relative_path)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == name:
            return True
        if isinstance(func, ast.Attribute) and func.attr == name:
            return True
    return False


def module_calls_store_method(
    relative_path: str,
    method_name: str,
) -> list[int]:
    """Return 1-based line numbers of store.<method_name>(...) calls."""
    tree = parse_module_ast(relative_path)
    lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == method_name
            and isinstance(func.value, ast.Name)
            and func.value.id == "store"
        ):
            lines.append(node.lineno)
    return lines


def append_jsonl_literal_paths(relative_path: str) -> list[str]:
    """Resolved first arguments to append_jsonl_record in a module."""
    tree = parse_module_ast(relative_path)
    paths: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (
            isinstance(func, ast.Attribute)
            and func.attr == "append_jsonl_record"
        ):
            continue
        if not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            paths.append(first.value)
            continue
        if isinstance(first, ast.Name) and first.id in _MEMDOC_PATH_CONSTANT_NAMES:
            paths.append(getattr(_memdoc_path_constants, first.id))
    return paths


def app_py_files_importing_or_calling(name: str) -> list[str]:
    """app/**/*.py files that import or call ``name`` (not docstring mentions)."""
    app_dir = repo_root() / "app"
    hits: list[str] = []
    for path in sorted(app_dir.rglob("*.py")):
        rel = path.relative_to(repo_root()).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    if alias.name == name:
                        hits.append(rel)
                        break
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == name:
                    hits.append(rel)
                    break
                if isinstance(func, ast.Attribute) and func.attr == name:
                    hits.append(rel)
                    break
    return sorted(set(hits))
