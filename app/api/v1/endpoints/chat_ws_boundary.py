"""Import boundary invariants for companion WebSocket ``/api/v1/chat/ws``.

``chat_ws.py`` and ``chat_ws_companion_support.py`` orchestrate HTTP/WS glue;
agentic intelligence must flow through ``companion_harness`` (and transitively
``living_sphere`` / ``techno_core``), not maintenance-mode ``app.core.agent`` or
``chat.py`` REST completions. Commercial glue (subscription, voice, chat_history)
in ``chat_ws.py`` is allowed; this module only blocks maintenance-mode agent stacks.

Enforced by ``tests/app/api/v1/endpoints/test_chat_ws_boundary.py``.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Final

_REPO_ROOT = Path(__file__).resolve().parents[4]

CHAT_WS_BOUNDARY_MODULE_PATHS: Final[tuple[str, ...]] = (
    "app/api/v1/endpoints/chat_ws.py",
    "app/api/v1/endpoints/chat_ws_companion_support.py",
)

CHAT_WS_REQUIRED_APP_CORE_PREFIX: Final[str] = "app.core.companion_harness"

CHAT_WS_ALLOWED_APP_CORE_PREFIXES: Final[tuple[str, ...]] = (
    CHAT_WS_REQUIRED_APP_CORE_PREFIX,
    "app.core.config",
    "app.core.model_selection",
)

CHAT_WS_FORBIDDEN_IMPORT_MODULES: Final[frozenset[str]] = frozenset(
    {
        "app.api.v1.endpoints.chat",
        "app.core.agent",
    }
)


def repo_root() -> Path:
    return _REPO_ROOT


def module_absolute_path(relative_path: str) -> Path:
    return repo_root() / relative_path


def parse_module_ast(relative_path: str) -> ast.Module:
    source = module_absolute_path(relative_path).read_text(encoding="utf-8")
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


def module_imports_companion_harness(relative_path: str) -> bool:
    prefix = CHAT_WS_REQUIRED_APP_CORE_PREFIX
    for mod in module_import_module_names(relative_path):
        if mod == prefix or mod.startswith(f"{prefix}."):
            return True
    return False


def module_imports_forbidden_maintenance_modules(
    relative_path: str,
) -> list[str]:
    hits: list[str] = []
    for mod in module_import_module_names(relative_path):
        for forbidden in CHAT_WS_FORBIDDEN_IMPORT_MODULES:
            if mod == forbidden or mod.startswith(f"{forbidden}."):
                hits.append(mod)
    return sorted(set(hits))


def module_app_core_imports_outside_allowlist(
    relative_path: str,
) -> list[str]:
    hits: list[str] = []
    for mod in module_import_module_names(relative_path):
        if not mod.startswith("app.core."):
            continue
        if any(mod.startswith(prefix) for prefix in CHAT_WS_ALLOWED_APP_CORE_PREFIXES):
            continue
        hits.append(mod)
    return sorted(set(hits))
