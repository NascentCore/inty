"""AST import extraction for intra-repo dependency analysis."""
from __future__ import annotations

import ast
from pathlib import Path

# Top-level repo packages (``import <name>``). Not exhaustive for stdlib/third-party.
INTRA_REPO_PACKAGE_ROOTS = frozenset(
    {
        "app",
        "backend",
        "experimental",
        "research",
        "tests",
        "tools",
    }
)


def resolve_from_module(
    file_path: Path, repo_root: Path, node: ast.ImportFrom
) -> str | None:
    """Resolve a ``from ... import`` node to an absolute module name."""
    if node.level == 0:
        return node.module

    relative_file = file_path.relative_to(repo_root).with_suffix("")
    package_parts = list(relative_file.parts[:-1])

    up_levels = node.level - 1
    if up_levels > len(package_parts):
        return None
    if up_levels:
        package_parts = package_parts[: len(package_parts) - up_levels]

    if node.module:
        package_parts += node.module.split(".")

    if not package_parts:
        return None
    return ".".join(package_parts)


def iter_imports(file_path: Path, repo_root: Path) -> list[tuple[str, int]]:
    """Return ``(imported_module, line_number)`` pairs from a Python file."""
    imports: list[tuple[str, int]] = []
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, node.lineno))
            continue

        if not isinstance(node, ast.ImportFrom):
            continue

        module = resolve_from_module(file_path, repo_root, node)
        if not module:
            continue

        if module == "app":
            for alias in node.names:
                candidate = f"app.{alias.name}"
                imports.append((candidate, node.lineno))
            continue

        imports.append((module, node.lineno))
    return imports


def module_name_for_file(repo_root: Path, file_path: Path) -> str:
    """Derive dotted module name from a repo-relative ``.py`` path."""
    relative = file_path.relative_to(repo_root).with_suffix("")
    return ".".join(relative.parts)


def package_name_for_module(module_name: str) -> str | None:
    """Return parent package for a module, or the root for single-segment modules."""
    root = module_name.split(".", 1)[0]
    if root not in INTRA_REPO_PACKAGE_ROOTS:
        return None
    parts = module_name.split(".")
    if len(parts) == 1:
        return root
    return ".".join(parts[:-1])


def is_intra_repo_module(module_name: str) -> bool:
    """Whether ``module_name`` belongs to a tracked intra-repo root."""
    root = module_name.split(".", 1)[0]
    return root in INTRA_REPO_PACKAGE_ROOTS
