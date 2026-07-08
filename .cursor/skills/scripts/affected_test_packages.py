#!/usr/bin/env python3
"""Package-level reverse-deps lookup for PR selective pytest targets."""
from __future__ import annotations

import json
import subprocess
import sys
from collections import deque
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from fnmatch import fnmatch
from pathlib import Path
from typing import Annotated

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import cyclopts
from loguru import logger

from python_import_scan import (
    INTRA_REPO_PACKAGE_ROOTS,
    is_intra_repo_module,
    iter_imports,
    module_name_for_file,
    package_name_for_module,
)

app = cyclopts.App(
    help="Select pytest directories affected by a git diff via package reverse-deps."
)

GRAPH_SCAN_TREES: tuple[str, ...] = ("app", "backend", "tests")

AFFECTED_RATIO_THRESHOLD = 0.6

FULL_SUITE_GLOB_PATTERNS: tuple[str, ...] = (
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

ARCH_LAYERS = frozenset(
    {
        "api",
        "schemas",
        "services",
        "models",
        "utils",
        "middleware",
        "external_services",
    }
)

FORBIDDEN_LAYER_DEPENDENCIES: frozenset[tuple[str, str]] = frozenset(
    {
        ("api", "middleware"),
        ("services", "middleware"),
        ("models", "services"),
        ("models", "schemas"),
        ("models", "external_services"),
        ("models", "middleware"),
        ("schemas", "external_services"),
        ("schemas", "middleware"),
        ("utils", "models"),
        ("utils", "middleware"),
        ("external_services", "api"),
        ("external_services", "services"),
        ("external_services", "models"),
        ("external_services", "middleware"),
    }
)

COMPANION_HARNESS_PREFIX = "app.core.companion_harness"
COMPANION_SERVING_PACKAGES = frozenset(
    {
        "app.core.companion_harness.agentic_companion",
        "app.core.companion_harness.loop",
        "app.core.companion_harness.runtime",
    }
)
COMPANION_KERNEL_PREFIX = "app.core.companion_harness.companion"
COMPANION_LEAF_PACKAGES = frozenset(
    {
        "app.core.companion_harness.prompting",
        "app.core.companion_harness.memory",
        "app.core.companion_harness.tools",
        "app.core.companion_harness.llm",
        "app.core.companion_harness.providers",
        "app.core.companion_harness.experience_profile",
    }
)


class FullSuiteReason(StrEnum):
    """Why selective pytest was skipped."""

    FORCED = "forced"
    GLOBAL_CHANGE = "global_change"
    RATIO_THRESHOLD = "ratio_threshold"
    NO_CHANGED_FILES = "no_changed_files"


@dataclass(frozen=True)
class Package:
    """Dotted intra-repo package id."""

    name: str

    def __post_init__(self) -> None:
        assert self.name
        root = self.name.split(".", 1)[0]
        assert root in INTRA_REPO_PACKAGE_ROOTS


@dataclass
class ImportGraph:
    """Package-level forward import edges."""

    forward: dict[str, set[str]] = field(default_factory=dict)

    def add_edge(self, importer: Package, imported: Package) -> None:
        if importer.name == imported.name:
            return
        self.forward.setdefault(importer.name, set()).add(imported.name)

    def packages(self) -> set[str]:
        names: set[str] = set()
        for importer, imported_set in self.forward.items():
            names.add(importer)
            names.update(imported_set)
        return names


@dataclass(frozen=True)
class ReverseDependencyIndex:
    """Reverse adjacency for package dependents."""

    reverse: dict[str, set[str]]

    @classmethod
    def from_forward(cls, graph: ImportGraph) -> ReverseDependencyIndex:
        reverse: dict[str, set[str]] = {}
        for importer, imported_set in graph.forward.items():
            for imported in imported_set:
                reverse.setdefault(imported, set()).add(importer)
        return cls(reverse=reverse)

    def transitive_dependents(self, seeds: set[Package]) -> set[Package]:
        seen: set[str] = set()
        queue: deque[str] = deque()
        for seed in seeds:
            if seed.name not in seen:
                seen.add(seed.name)
                queue.append(seed.name)
        while queue:
            current = queue.popleft()
            for dependent in self.reverse.get(current, ()):
                if dependent in seen:
                    continue
                seen.add(dependent)
                queue.append(dependent)
        return {Package(name) for name in seen}


@dataclass(frozen=True)
class BoundaryViolation:
    """Architectural import edge that violates documented layering."""

    importer_package: str
    imported_package: str
    rule: str
    fan_in: int


@dataclass(frozen=True)
class AffectedTestPlan:
    """Selective pytest plan for a git diff."""

    run_all: bool
    test_dirs: tuple[str, ...]
    changed_packages: tuple[str, ...]
    affected_test_packages: tuple[str, ...]
    full_suite_reason: str | None
    affected_ratio: float


def _package_from_module(module_name: str) -> Package | None:
    package = package_name_for_module(module_name)
    if package is None:
        return None
    return Package(package)


def _package_for_file(repo_root: Path, file_path: Path) -> Package | None:
    module_name = module_name_for_file(repo_root, file_path)
    return _package_from_module(module_name)


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
            importer = _package_for_file(repo_root, file_path)
            if importer is None:
                continue
            graph.forward.setdefault(importer.name, set())
            try:
                imported_modules = iter_imports(file_path, repo_root)
            except SyntaxError as exc:
                logger.error(f"Failed to parse {file_path}: {exc}")
                raise
            for imported_module, _line_number in imported_modules:
                if not is_intra_repo_module(imported_module):
                    continue
                imported = _package_from_module(imported_module)
                if imported is None:
                    continue
                graph.add_edge(importer, imported)
    return graph


def mirror_test_package(source: Package) -> Package | None:
    """Map a source package to its mirrored tests package."""
    name = source.name
    if name.startswith("app.living_sphere"):
        suffix = name.removeprefix("app.living_sphere")
        mirrored = "tests.living_sphere" + suffix
        return Package(mirrored)
    if name.startswith("app."):
        mirrored = "tests.app." + name.removeprefix("app.")
        return Package(mirrored)
    if name.startswith("backend."):
        mirrored = "tests.backend." + name.removeprefix("backend.")
        return Package(mirrored)
    return None


def package_to_directory(package_name: str) -> str:
    """Convert dotted package name to repo-relative directory path."""
    return package_name.replace(".", "/")


def pytest_paths_for_test_packages(
    packages: set[Package],
    repo_root: Path,
) -> tuple[str, ...]:
    """Map affected test packages to non-overlapping pytest path arguments."""
    package_names = {package.name for package in packages}
    sorted_names = sorted(
        package_names,
        key=lambda name: (-name.count("."), name),
    )
    claimed_prefixes: list[str] = []
    dir_paths: list[str] = []
    file_paths: set[str] = set()

    for name in sorted_names:
        rel_dir = Path(package_to_directory(name))
        full_dir = repo_root / rel_dir
        if not full_dir.is_dir():
            continue
        rel_posix = rel_dir.as_posix()
        nested_under_claimed = any(
            rel_posix == prefix or rel_posix.startswith(prefix + "/")
            for prefix in claimed_prefixes
        )
        if nested_under_claimed:
            for py_file in sorted(full_dir.glob("*.py")):
                if py_file.name == "__init__.py":
                    continue
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
            full_dir = repo_root / directory
            for py_file in sorted(full_dir.glob("*.py")):
                if py_file.name != "__init__.py":
                    file_paths.add(py_file.relative_to(repo_root).as_posix())
            continue
        pruned_dirs.append(directory)

    return tuple(sorted(set(pruned_dirs) | file_paths))


def list_test_packages(graph: ImportGraph) -> set[Package]:
    """All test packages present in the import graph."""
    return {
        Package(name)
        for name in graph.packages()
        if name.startswith("tests.")
    }


def _matches_full_suite_pattern(changed_path: str) -> bool:
    normalized = changed_path.replace("\\", "/")
    for pattern in FULL_SUITE_GLOB_PATTERNS:
        if fnmatch(normalized, pattern):
            return True
    return False


def _full_suite_reason_for_changes(changed_files: tuple[str, ...]) -> FullSuiteReason | None:
    for changed_path in changed_files:
        if _matches_full_suite_pattern(changed_path):
            return FullSuiteReason.GLOBAL_CHANGE
        if changed_path.startswith("app/") and not changed_path.endswith(".py"):
            return FullSuiteReason.GLOBAL_CHANGE
    return None


def git_changed_files(
    repo_root: Path,
    base_ref: str,
    head_ref: str,
) -> tuple[str, ...]:
    """Return repo-relative paths changed between base and head."""
    result = subprocess.run(
        ["git", "diff", "--name-only", base_ref, head_ref],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    lines = [line.replace("\\", "/") for line in result.stdout.splitlines() if line]
    return tuple(lines)


def changed_packages_for_files(
    repo_root: Path,
    changed_files: tuple[str, ...],
) -> set[Package]:
    """Resolve changed Python files to parent packages."""
    packages: set[Package] = set()
    for changed_path in changed_files:
        if not changed_path.endswith(".py"):
            continue
        file_path = repo_root / changed_path
        if not file_path.is_file():
            continue
        package = _package_for_file(repo_root, file_path)
        if package is not None:
            packages.add(package)
    return packages


def select_affected_tests(
    repo_root: Path,
    changed_files: tuple[str, ...],
    graph: ImportGraph,
    reverse_index: ReverseDependencyIndex,
    force_full_suite: bool,
) -> AffectedTestPlan:
    """Compute selective pytest targets for a change set."""
    if force_full_suite:
        return AffectedTestPlan(
            run_all=True,
            test_dirs=(),
            changed_packages=(),
            affected_test_packages=(),
            full_suite_reason=FullSuiteReason.FORCED.value,
            affected_ratio=1.0,
        )

    if not changed_files:
        return AffectedTestPlan(
            run_all=True,
            test_dirs=(),
            changed_packages=(),
            affected_test_packages=(),
            full_suite_reason=FullSuiteReason.NO_CHANGED_FILES.value,
            affected_ratio=1.0,
        )

    global_reason = _full_suite_reason_for_changes(changed_files)
    if global_reason is not None:
        return AffectedTestPlan(
            run_all=True,
            test_dirs=(),
            changed_packages=tuple(
                sorted(package.name for package in changed_packages_for_files(repo_root, changed_files))
            ),
            affected_test_packages=(),
            full_suite_reason=global_reason.value,
            affected_ratio=1.0,
        )

    changed_packages = changed_packages_for_files(repo_root, changed_files)
    dependents = reverse_index.transitive_dependents(changed_packages)

    affected_packages = set(changed_packages)
    affected_packages.update(dependents)

    for package in changed_packages:
        mirrored = mirror_test_package(package)
        if mirrored is not None:
            affected_packages.add(mirrored)

    test_packages = {
        package
        for package in affected_packages
        if package.name.startswith("tests.")
    }
    all_test_packages = list_test_packages(graph)
    ratio = len(test_packages) / len(all_test_packages) if all_test_packages else 1.0

    if ratio >= AFFECTED_RATIO_THRESHOLD:
        return AffectedTestPlan(
            run_all=True,
            test_dirs=(),
            changed_packages=tuple(sorted(package.name for package in changed_packages)),
            affected_test_packages=tuple(sorted(package.name for package in test_packages)),
            full_suite_reason=FullSuiteReason.RATIO_THRESHOLD.value,
            affected_ratio=ratio,
        )

    test_dirs = pytest_paths_for_test_packages(test_packages, repo_root)
    return AffectedTestPlan(
        run_all=False,
        test_dirs=test_dirs,
        changed_packages=tuple(sorted(package.name for package in changed_packages)),
        affected_test_packages=tuple(sorted(package.name for package in test_packages)),
        full_suite_reason=None,
        affected_ratio=ratio,
    )


def _app_layer(package_name: str) -> str | None:
    if not package_name.startswith("app."):
        return None
    parts = package_name.split(".")
    if len(parts) < 2:
        return None
    layer = parts[1]
    if layer in ARCH_LAYERS:
        return layer
    return None


def _companion_harness_boundary_rule(
    importer_package: str,
    imported_package: str,
) -> str | None:
    if not imported_package.startswith(COMPANION_HARNESS_PREFIX):
        return None
    if importer_package.startswith(COMPANION_HARNESS_PREFIX):
        if imported_package.startswith(COMPANION_KERNEL_PREFIX):
            if importer_package.startswith(COMPANION_KERNEL_PREFIX):
                return None
            if importer_package in COMPANION_SERVING_PACKAGES:
                return None
            if importer_package in COMPANION_LEAF_PACKAGES:
                return (
                    "Companion leaf packages must not import companion kernel "
                    "turn orchestration."
                )
        return None
    if _app_layer(importer_package) in {"schemas", "models"}:
        return (
            f"{_app_layer(importer_package)} layer must not import companion "
            "harness kernel types."
        )
    return None


def boundary_violations(graph: ImportGraph) -> list[BoundaryViolation]:
    """Report app layer and companion harness boundary violations."""
    reverse_index = ReverseDependencyIndex.from_forward(graph)
    violations: list[BoundaryViolation] = []

    for importer, imported_set in sorted(graph.forward.items()):
        importer_layer = _app_layer(importer)
        for imported in sorted(imported_set):
            rule: str | None = None
            if importer_layer is not None:
                imported_layer = _app_layer(imported)
                if imported_layer is not None:
                    if (importer_layer, imported_layer) in FORBIDDEN_LAYER_DEPENDENCIES:
                        rule = (
                            f"app {importer_layer} must not depend on app "
                            f"{imported_layer}."
                        )
            if rule is None:
                rule = _companion_harness_boundary_rule(importer, imported)
            if rule is None:
                continue
            violations.append(
                BoundaryViolation(
                    importer_package=importer,
                    imported_package=imported,
                    rule=rule,
                    fan_in=len(reverse_index.reverse.get(imported, ())),
                )
            )
    return violations


def boundary_report_payload(graph: ImportGraph) -> dict[str, object]:
    """JSON-serializable boundary cleanliness report."""
    reverse_index = ReverseDependencyIndex.from_forward(graph)
    fan_in: dict[str, int] = {
        package: len(dependents)
        for package, dependents in reverse_index.reverse.items()
    }
    fan_out: dict[str, int] = {
        package: len(imports) for package, imports in graph.forward.items()
    }
    top_fan_in = sorted(fan_in.items(), key=lambda item: item[1], reverse=True)[:20]
    top_fan_out = sorted(fan_out.items(), key=lambda item: item[1], reverse=True)[:20]
    violations = boundary_violations(graph)
    return {
        "top_fan_in": [{"package": name, "count": count} for name, count in top_fan_in],
        "top_fan_out": [
            {"package": name, "count": count} for name, count in top_fan_out
        ],
        "violations": [asdict(violation) for violation in violations],
        "violation_count": len(violations),
    }


def plan_to_public_dict(plan: AffectedTestPlan) -> dict[str, object]:
    """Serialize an affected test plan for CI logs."""
    return asdict(plan)


@app.default
def main(
    base_ref: Annotated[
        str,
        cyclopts.Parameter(
            name="--base-ref",
            help="Git base ref for the diff (e.g. origin/main).",
        ),
    ] = "origin/main",
    head_ref: Annotated[
        str,
        cyclopts.Parameter(
            name="--head-ref",
            help="Git head ref for the diff (e.g. HEAD).",
        ),
    ] = "HEAD",
    repo_root: Annotated[
        str,
        cyclopts.Parameter(
            name="--repo-root",
            help="Repository root.",
        ),
    ] = ".",
    json_output: Annotated[
        bool,
        cyclopts.Parameter(
            name="--json",
            help="Print AffectedTestPlan JSON to stdout.",
        ),
    ] = False,
    boundary_report: Annotated[
        bool,
        cyclopts.Parameter(
            name="--boundary-report",
            help="Print boundary cleanliness JSON and exit.",
        ),
    ] = False,
    force_full_suite: Annotated[
        bool,
        cyclopts.Parameter(
            name="--force-full-suite",
            help="Skip selective logic and return run_all=true.",
        ),
    ] = False,
) -> None:
    root = Path(repo_root).resolve()
    graph = build_import_graph(root)

    if boundary_report:
        payload = boundary_report_payload(graph)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        raise SystemExit(0)

    changed_files = git_changed_files(root, base_ref, head_ref)
    reverse_index = ReverseDependencyIndex.from_forward(graph)
    plan = select_affected_tests(
        repo_root=root,
        changed_files=changed_files,
        graph=graph,
        reverse_index=reverse_index,
        force_full_suite=force_full_suite,
    )

    if json_output:
        print(json.dumps(plan_to_public_dict(plan), ensure_ascii=False, indent=2))
    elif plan.run_all:
        print("ALL")
    else:
        print(" ".join(plan.test_dirs))

    raise SystemExit(0)


if __name__ == "__main__":
    app()
