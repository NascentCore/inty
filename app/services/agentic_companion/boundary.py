"""Import boundary invariants for ``app.services.agentic_companion``.

This package glues ``companion_harness`` runtime, ``agentic_channel`` adapters,
and ``/api/v1/chat/ws`` orchestration. It must not embed agent turn-engine or
inner-tick scheduling logic — those live under ``app.core.companion_harness``.

Enforced by ``tests/app/services/agentic_companion/test_agentic_companion_boundary.py``.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Final

_REPO_ROOT = Path(__file__).resolve().parents[3]

AGENTIC_COMPANION_SCAN_ROOT: Final[str] = "app/services/agentic_companion"

AGENTIC_COMPANION_ALLOWED_HARNESS_PREFIXES: Final[tuple[str, ...]] = (
    "app.core.companion_harness.companion.models",
    "app.core.companion_harness.companion.runtime_channel",
    "app.core.companion_harness.companion.turn_routes",
    "app.core.companion_harness.companion.scope",
    "app.core.companion_harness.companion.scope_turn_lock",
    "app.core.companion_harness.companion.langsmith_turn_slice",
    "app.core.companion_harness.companion.dreaming_observability",
    "app.core.companion_harness.companion.manager",
    "app.core.companion_harness.runtime",
    "app.core.companion_harness.agent_channel",
    "app.core.companion_harness.memory.memory_store",
    "app.core.companion_harness.memory.companion_scope_listing",
    "app.core.companion_harness.tools",
)

AGENTIC_COMPANION_FORBIDDEN_HARNESS_PREFIXES: Final[tuple[str, ...]] = (
    "app.core.companion_harness.companion.turn_engine",
    "app.core.companion_harness.companion.turn_pipeline",
    "app.core.companion_harness.companion.turn",
    "app.core.companion_harness.companion.inner_tick_schedule",
    "app.core.companion_harness.companion.proactive_chat",
    "app.core.companion_harness.companion.schedule_queue",
    "app.core.companion_harness.companion.prompt_stack",
    "app.core.companion_harness.companion.llm_chat_runtime",
)


def repo_root() -> Path:
    return _REPO_ROOT


def agentic_companion_python_paths() -> list[str]:
    root = repo_root() / AGENTIC_COMPANION_SCAN_ROOT
    return sorted(
        str(path.relative_to(repo_root()))
        for path in root.rglob("*.py")
        if path.name != "boundary.py"
    )


def parse_module_ast(relative_path: str) -> ast.Module:
    source = (repo_root() / relative_path).read_text(encoding="utf-8")
    return ast.parse(source, filename=relative_path)


def module_import_module_names(relative_path: str) -> list[str]:
    tree = parse_module_ast(relative_path)
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def module_forbidden_harness_imports(relative_path: str) -> list[str]:
    hits: list[str] = []
    for mod in module_import_module_names(relative_path):
        for forbidden in AGENTIC_COMPANION_FORBIDDEN_HARNESS_PREFIXES:
            if mod == forbidden or mod.startswith(f"{forbidden}."):
                hits.append(mod)
    return sorted(set(hits))


def module_disallowed_harness_imports(relative_path: str) -> list[str]:
    """Harness imports outside the glue allowlist (excluding forbidden — checked separately)."""
    hits: list[str] = []
    for mod in module_import_module_names(relative_path):
        if not mod.startswith("app.core.companion_harness."):
            continue
        if any(
            mod == prefix or mod.startswith(f"{prefix}.")
            for prefix in AGENTIC_COMPANION_ALLOWED_HARNESS_PREFIXES
        ):
            continue
        if any(
            mod == prefix or mod.startswith(f"{prefix}.")
            for prefix in AGENTIC_COMPANION_FORBIDDEN_HARNESS_PREFIXES
        ):
            continue
        hits.append(mod)
    return sorted(set(hits))
