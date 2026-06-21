"""Import boundary invariants for companion WebSocket ``/api/v1/chat/ws``.

``chat_ws.py`` and ``chat_ws_companion_support.py`` orchestrate HTTP/WS glue;
agentic intelligence must flow through ``companion_harness`` (and transitively
``living_sphere`` / ``techno_core``), not maintenance-mode ``app.core.agent`` or
``chat.py`` REST completions. Commercial glue (subscription, voice, chat_history)
in ``chat_ws.py`` is allowed; this module only blocks maintenance-mode agent stacks.

Production companion surfaces must not **read or write** legacy ``readable_id``
(maintenance-mode HTTP APIs may still touch it for old clients).

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

# Trees scanned for legacy ``readable_id`` identifier use (companion + agent-channel production).
COMPANION_NO_READABLE_ID_SCAN_ROOTS: Final[tuple[str, ...]] = (
    "app/core/companion_harness",
    "app/services/agentic_companion",
    "app/services/agentic_channel",
    "living_sphere",
    "techno_core",
    "backend/ops/telegram_demo",
    "backend/ops/weixin_onboard",
)

COMPANION_NO_READABLE_ID_SCAN_FILES: Final[tuple[str, ...]] = (
    *CHAT_WS_BOUNDARY_MODULE_PATHS,
    "app/schemas/chat_websocket.py",
    "app/services/companion_chat_service.py",
    "app/services/chat_websocket_session.py",
    "app/services/chat_completion_wire.py",
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
        if any(
            mod.startswith(prefix)
            for prefix in CHAT_WS_ALLOWED_APP_CORE_PREFIXES
        ):
            continue
        hits.append(mod)
    return sorted(set(hits))


def companion_production_python_paths() -> list[str]:
    """Relative paths for companion harness, agent-channel, and ``/api/v1/chat/ws`` glue."""
    paths: list[str] = []
    for rel_root in COMPANION_NO_READABLE_ID_SCAN_ROOTS:
        root = repo_root() / rel_root
        for path in sorted(root.rglob("*.py")):
            paths.append(str(path.relative_to(repo_root())))
    paths.extend(COMPANION_NO_READABLE_ID_SCAN_FILES)
    return sorted(set(paths))


_READABLE_ID = "readable_id"


def _is_readable_id_constant(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and node.value == _READABLE_ID


def _collect_readable_id_hits(tree: ast.AST, relative_path: str) -> list[str]:
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == _READABLE_ID:
            hits.append(f"{relative_path}:L{node.lineno}:name")
        elif isinstance(node, ast.Attribute) and node.attr == _READABLE_ID:
            hits.append(f"{relative_path}:L{node.lineno}:attribute")
        elif isinstance(node, ast.keyword) and node.arg == _READABLE_ID:
            hits.append(f"{relative_path}:L{node.lineno}:keyword")
        elif isinstance(node, ast.Subscript) and _is_readable_id_constant(
            node.slice
        ):
            hits.append(f"{relative_path}:L{node.lineno}:subscript")
        elif isinstance(node, ast.Dict):
            for key in node.keys:
                if key is not None and _is_readable_id_constant(key):
                    hits.append(f"{relative_path}:L{key.lineno}:dict_key")
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and len(node.args) >= 2
            and _is_readable_id_constant(node.args[1])
        ):
            hits.append(f"{relative_path}:L{node.lineno}:getattr")
    return hits


def ast_readable_id_references(relative_path: str) -> list[str]:
    """Return hits when source uses ``readable_id`` as an identifier (not string literals)."""
    tree = parse_module_ast(relative_path)
    return _collect_readable_id_hits(tree, relative_path)


def ast_readable_id_references_in_source(
    relative_path: str,
    source: str,
) -> list[str]:
    """Same as ``ast_readable_id_references`` but for in-memory source (tests)."""
    tree = ast.parse(source, filename=relative_path)
    return _collect_readable_id_hits(tree, relative_path)


def companion_surface_readable_id_references() -> list[str]:
    """Aggregate ``readable_id`` references across production companion modules.

    AST scan catches identifier forms (name, attribute, keyword, dict key, subscript,
    ``getattr(..., "readable_id")``). It does not see dynamic string assembly or raw
    SQL literals — keep companion production code on ``user_id`` / ``agent_id`` anyway.
    """
    hits: list[str] = []
    for rel in companion_production_python_paths():
        hits.extend(ast_readable_id_references(rel))
    return sorted(hits)
