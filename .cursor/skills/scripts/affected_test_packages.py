#!/usr/bin/env python3
"""Package-level reverse-deps lookup for PR selective pytest targets."""
from __future__ import annotations

import ast
import json
import subprocess
import sys
from collections import deque
from dataclasses import asdict, dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Annotated

import cyclopts

app = cyclopts.App(
    help="Select pytest directories affected by a git diff via package reverse-deps."
)

INTRA_REPO_ROOTS = frozenset({"app", "backend", "tests", "tools"})
GRAPH_SCAN_TREES = ("app", "backend", "tests")
AFFECTED_RATIO_THRESHOLD = 0.6
FULL_SUITE_GLOB_PATTERNS = (
    "pytest.ini",
    "requirements.txt",
    "tests/requirements.txt",
    "devops/config.yaml.test",
    "tests/conftest.py",
    "tests/fixtures/**",
    "tests/**/conftest.py",
    "backend/alembic/**",
    "backend/inty/start.sh",
    "backend/push_worker/**",
    ".github/workflows/ci_backend.yaml",
    ".cursor/skills/scripts/check_*.py",
)


@dataclass
class ImportGraph:
    """Package-level forward import edges."""

    forward: dict[str, set[str]] = field(default_factory=dict)

    def add_edge(self, importer: str, imported: str) -> None:
        if importer == imported:
            return
        self.forward.setdefault(importer, set()).add(imported)

    def packages(self) -> set[str]:
        names: set[str] = set()
        for importer, imported_set in self.forward.items():
            names.add(importer)
            names.update(imported_set)
        return names


@dataclass(frozen=True)
class AffectedTestPlan:
    """Selective pytest plan for a git diff."""

    run_all: bool
    test_dirs: tuple[str, ...]
    changed_packages: tuple[str, ...]
    affected_test_packages: tuple[str, ...]
    full_suite_reason: str | None
    affected_ratio: float


def _resolve_from_module(
    file_path: Path, repo_root: Path, node: ast.ImportFrom
) -> str | None:
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


def _iter_imports(file_path: Path, repo_root: Path) -> list[str]:
    imports: list[str] = []
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
            continue
        if not isinstance(node, ast.ImportFrom):
            continue
        module = _resolve_from_module(file_path, repo_root, node)
        if not module:
            continue
        if module == "app":
            for alias in node.names:
                imports.append(f"app.{alias.name}")
            continue
        imports.append(module)
    return imports


def _module_name(file_path: Path, repo_root: Path) -> str:
    return ".".join(file_path.relative_to(repo_root).with_suffix("").parts)


def _package_name(module_name: str) -> str | None:
    root = module_name.split(".", 1)[0]
    if root not in INTRA_REPO_ROOTS:
        return None
    parts = module_name.split(".")
    if len(parts) == 1:
        return root
    return ".".join(parts[:-1])


def _is_intra_repo(module_name: str) -> bool:
    return module_name.split(".", 1)[0] in INTRA_REPO_ROOTS


def build_import_graph(repo_root: Path) -> ImportGraph:
    """Scan app/backend/tests and build package-level forward edges."""
    graph = ImportGraph()
    for tree_name in GRAPH_SCAN_TREES:
        tree_root = repo_root / tree_name
        if not tree_root.is_dir():
            continue
        for file_path in sorted(tree_root.rglob("*.py")):
            if "experimental" in file_path.parts or "research" in file_path.parts:
                continue
            importer = _package_name(_module_name(file_path, repo_root))
            if importer is None:
                continue
            graph.forward.setdefault(importer, set())
            for imported_module in _iter_imports(file_path, repo_root):
                if not _is_intra_repo(imported_module):
                    continue
                imported = _package_name(imported_module)
                if imported is None:
                    continue
                graph.add_edge(importer, imported)
    return graph


def _reverse_index(graph: ImportGraph) -> dict[str, set[str]]:
    reverse: dict[str, set[str]] = {}
    for importer, imported_set in graph.forward.items():
        for imported in imported_set:
            reverse.setdefault(imported, set()).add(importer)
    return reverse


def _transitive_dependents(
    reverse: dict[str, set[str]], seeds: set[str]
) -> set[str]:
    seen = set(seeds)
    queue = deque(seeds)
    while queue:
        current = queue.popleft()
        for dependent in reverse.get(current, ()):
            if dependent in seen:
                continue
            seen.add(dependent)
            queue.append(dependent)
    return seen


def _mirror_test_package(source: str) -> str | None:
    if source.startswith("app.living_sphere"):
        return "tests.living_sphere" + source.removeprefix("app.living_sphere")
    if source.startswith("app."):
        return "tests.app." + source.removeprefix("app.")
    if source.startswith("backend."):
        return "tests.backend." + source.removeprefix("backend.")
    return None


def _pytest_paths(packages: set[str], repo_root: Path) -> tuple[str, ...]:
    sorted_names = sorted(packages, key=lambda name: (-name.count("."), name))
    claimed_prefixes: list[str] = []
    dir_paths: list[str] = []
    file_paths: set[str] = set()

    for name in sorted_names:
        rel_dir = Path(name.replace(".", "/"))
        full_dir = repo_root / rel_dir
        if not full_dir.is_dir():
            continue
        rel_posix = rel_dir.as_posix()
        if any(
            rel_posix == prefix or rel_posix.startswith(prefix + "/")
            for prefix in claimed_prefixes
        ):
            for py_file in sorted(full_dir.glob("*.py")):
                if py_file.name != "__init__.py":
                    file_paths.add(py_file.relative_to(repo_root).as_posix())
            continue
        dir_paths.append(rel_posix)
        claimed_prefixes.append(rel_posix)

    pruned_dirs: list[str] = []
    dir_path_set = set(dir_paths)
    for directory in sorted(dir_path_set, key=lambda value: (-value.count("/"), value)):
        if any(
            other != directory and other.startswith(directory + "/")
            for other in dir_path_set
        ):
            for py_file in sorted((repo_root / directory).glob("*.py")):
                if py_file.name != "__init__.py":
                    file_paths.add(py_file.relative_to(repo_root).as_posix())
            continue
        pruned_dirs.append(directory)
    return tuple(sorted(set(pruned_dirs) | file_paths))


def _changed_packages(repo_root: Path, changed_files: tuple[str, ...]) -> set[str]:
    packages: set[str] = set()
    for changed_path in changed_files:
        if not changed_path.endswith(".py"):
            continue
        file_path = repo_root / changed_path
        if not file_path.is_file():
            continue
        package = _package_name(_module_name(file_path, repo_root))
        if package is not None:
            packages.add(package)
    return packages


def _matches_full_suite_pattern(changed_path: str) -> bool:
    normalized = changed_path.replace("\\", "/")
    return any(fnmatch(normalized, pattern) for pattern in FULL_SUITE_GLOB_PATTERNS)


def git_changed_files(repo_root: Path, base_ref: str, head_ref: str) -> tuple[str, ...]:
    result = subprocess.run(
        ["git", "diff", "--name-only", base_ref, head_ref],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return tuple(line.replace("\\", "/") for line in result.stdout.splitlines() if line)


def select_affected_tests(
    repo_root: Path,
    changed_files: tuple[str, ...],
    graph: ImportGraph,
    reverse: dict[str, set[str]],
) -> AffectedTestPlan:
    """Compute selective pytest targets for a change set."""
    if not changed_files:
        return AffectedTestPlan(True, (), (), (), "no_changed_files", 1.0)

    for changed_path in changed_files:
        if _matches_full_suite_pattern(changed_path):
            return AffectedTestPlan(
                True,
                (),
                tuple(sorted(_changed_packages(repo_root, changed_files))),
                (),
                "global_change",
                1.0,
            )
        if changed_path.startswith("app/") and not changed_path.endswith(".py"):
            return AffectedTestPlan(
                True,
                (),
                tuple(sorted(_changed_packages(repo_root, changed_files))),
                (),
                "global_change",
                1.0,
            )

    changed_packages = _changed_packages(repo_root, changed_files)
    affected_packages = _transitive_dependents(reverse, set(changed_packages))
    for package in changed_packages:
        mirrored = _mirror_test_package(package)
        if mirrored is not None:
            affected_packages.add(mirrored)

    test_packages = {
        package for package in affected_packages if package.startswith("tests.")
    }
    all_test_packages = {
        package for package in graph.packages() if package.startswith("tests.")
    }
    ratio = len(test_packages) / len(all_test_packages) if all_test_packages else 1.0

    if ratio >= AFFECTED_RATIO_THRESHOLD:
        return AffectedTestPlan(
            True,
            (),
            tuple(sorted(changed_packages)),
            tuple(sorted(test_packages)),
            "ratio_threshold",
            ratio,
        )

    return AffectedTestPlan(
        False,
        _pytest_paths(test_packages, repo_root),
        tuple(sorted(changed_packages)),
        tuple(sorted(test_packages)),
        None,
        ratio,
    )


@app.default
def main(
    base_ref: Annotated[
        str,
        cyclopts.Parameter(name="--base-ref", help="Git base ref."),
    ] = "origin/main",
    head_ref: Annotated[
        str,
        cyclopts.Parameter(name="--head-ref", help="Git head ref."),
    ] = "HEAD",
    repo_root: Annotated[
        str,
        cyclopts.Parameter(name="--repo-root", help="Repository root."),
    ] = ".",
    json_output: Annotated[
        bool,
        cyclopts.Parameter(name="--json", help="Print AffectedTestPlan JSON."),
    ] = False,
) -> None:
    root = Path(repo_root).resolve()
    graph = build_import_graph(root)
    reverse = _reverse_index(graph)
    plan = select_affected_tests(
        root,
        git_changed_files(root, base_ref, head_ref),
        graph,
        reverse,
    )
    if json_output:
        print(json.dumps(asdict(plan), ensure_ascii=False, indent=2))
    elif plan.run_all:
        print("ALL")
    else:
        print(" ".join(plan.test_dirs))
    raise SystemExit(0)


if __name__ == "__main__":
    app()
