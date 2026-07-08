"""Tests for affected_test_packages selective pytest planning."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[4] / ".cursor" / "skills" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from affected_test_packages import (  # noqa: E402
    FullSuiteReason,
    ImportGraph,
    Package,
    ReverseDependencyIndex,
    boundary_violations,
    build_import_graph,
    changed_packages_for_files,
    mirror_test_package,
    pytest_paths_for_test_packages,
    select_affected_tests,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _init_repo(repo_root: Path) -> None:
    repo_root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )


def _seed_mini_repo(repo_root: Path) -> None:
    _write(
        repo_root / "app" / "alpha" / "core.py",
        "VALUE = 1\n",
    )
    _write(
        repo_root / "app" / "beta" / "service.py",
        "from app.alpha.core import VALUE\n",
    )
    _write(
        repo_root / "backend" / "ops" / "channel.py",
        "from app.beta.service import VALUE\n",
    )
    _write(
        repo_root / "tests" / "app" / "alpha" / "test_core.py",
        "from app.alpha.core import VALUE\n",
    )
    _write(
        repo_root / "tests" / "app" / "beta" / "test_service.py",
        "from app.beta.service import VALUE\n",
    )
    _write(
        repo_root / "tests" / "backend" / "ops" / "test_channel.py",
        "from backend.ops.channel import VALUE\n",
    )
    _write(
        repo_root / "tests" / "fixtures" / "shared.py",
        "SHARED = True\n",
    )
    _write(
        repo_root / "tests" / "app" / "beta" / "companion_test_fixtures.py",
        "from tests.fixtures.shared import SHARED\n",
    )
    _write(
        repo_root / "tests" / "app" / "gamma" / "test_gamma.py",
        "from tests.app.beta.companion_test_fixtures import SHARED\n",
    )
    _write(
        repo_root / "app" / "living_sphere" / "models.py",
        "MODEL = 'living'\n",
    )
    _write(
        repo_root / "tests" / "living_sphere" / "test_models.py",
        "from app.living_sphere.models import MODEL\n",
    )
    for index in range(8):
        _write(
            repo_root / "tests" / "isolated" / f"pkg{index}" / "test_isolated.py",
            f"ISOLATED_{index} = {index}\n",
        )


def test_mirror_test_package_living_sphere_exception() -> None:
    mirrored = mirror_test_package(Package("app.living_sphere.models"))
    assert mirrored is not None
    assert mirrored.name == "tests.living_sphere.models"


def test_reverse_bfs_selects_transitive_test_packages(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _seed_mini_repo(repo_root)
    graph = build_import_graph(repo_root)
    reverse_index = ReverseDependencyIndex.from_forward(graph)

    changed_packages = changed_packages_for_files(
        repo_root,
        ("app/alpha/core.py",),
    )
    plan = select_affected_tests(
        repo_root=repo_root,
        changed_files=("app/alpha/core.py",),
        graph=graph,
        reverse_index=reverse_index,
        force_full_suite=False,
    )

    assert plan.run_all is False
    assert "tests.app.alpha" in plan.affected_test_packages
    assert "tests.app.beta" in plan.affected_test_packages
    assert "tests.backend.ops" in plan.affected_test_packages


def test_mirror_adds_living_sphere_tests_for_source_change(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _seed_mini_repo(repo_root)
    graph = build_import_graph(repo_root)
    reverse_index = ReverseDependencyIndex.from_forward(graph)

    plan = select_affected_tests(
        repo_root=repo_root,
        changed_files=("app/living_sphere/models.py",),
        graph=graph,
        reverse_index=reverse_index,
        force_full_suite=False,
    )

    assert plan.run_all is False
    assert "tests.living_sphere" in plan.affected_test_packages
    assert "tests/living_sphere" in plan.test_dirs


def test_test_to_test_fixture_chain(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _seed_mini_repo(repo_root)
    graph = build_import_graph(repo_root)
    reverse_index = ReverseDependencyIndex.from_forward(graph)

    plan = select_affected_tests(
        repo_root=repo_root,
        changed_files=(
            "tests/app/beta/companion_test_fixtures.py",
        ),
        graph=graph,
        reverse_index=reverse_index,
        force_full_suite=False,
    )

    assert plan.run_all is False
    assert "tests.app.beta" in plan.affected_test_packages
    assert "tests.app.gamma" in plan.affected_test_packages


def test_global_change_triggers_full_suite(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _seed_mini_repo(repo_root)
    graph = build_import_graph(repo_root)
    reverse_index = ReverseDependencyIndex.from_forward(graph)

    plan = select_affected_tests(
        repo_root=repo_root,
        changed_files=("tests/conftest.py",),
        graph=graph,
        reverse_index=reverse_index,
        force_full_suite=False,
    )

    assert plan.run_all is True
    assert plan.full_suite_reason == FullSuiteReason.GLOBAL_CHANGE.value


def test_ratio_threshold_triggers_full_suite(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    graph = ImportGraph()
    test_packages = [f"tests.pkg{i}" for i in range(10)]
    for name in test_packages:
        graph.forward[name] = set()
    graph.forward["tests.pkg0"].add("app.alpha")

    reverse_index = ReverseDependencyIndex(
        reverse={
            "tests.pkg0": set(test_packages[1:]),
        }
    )
    _write(repo_root / "tests" / "pkg0" / "module.py", "VALUE = 1\n")

    plan = select_affected_tests(
        repo_root=repo_root,
        changed_files=("tests/pkg0/module.py",),
        graph=graph,
        reverse_index=reverse_index,
        force_full_suite=False,
    )

    assert plan.run_all is True
    assert plan.full_suite_reason == FullSuiteReason.RATIO_THRESHOLD.value
    assert plan.affected_ratio == 1.0


def test_pytest_paths_prune_parent_when_child_selected(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _write(repo_root / "tests" / "app" / "root_case.py", "X = 1\n")
    _write(repo_root / "tests" / "app" / "child" / "test_child.py", "X = 1\n")

    paths = pytest_paths_for_test_packages(
        {
            Package("tests.app"),
            Package("tests.app.child"),
        },
        repo_root,
    )

    assert "tests/app/child" in paths
    assert "tests/app" not in paths
    assert "tests/app/root_case.py" in paths


def test_boundary_violations_detects_schemas_to_harness(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _write(
        repo_root / "app" / "schemas" / "chat.py",
        "from app.core.companion_harness.companion.inner_tick_kind import InnerTickKind\n",
    )
    _write(
        repo_root / "app" / "core" / "companion_harness" / "companion" / "inner_tick_kind.py",
        "class InnerTickKind: ...\n",
    )
    graph = build_import_graph(repo_root)
    violations = boundary_violations(graph)
    assert any(
        violation.importer_package == "app.schemas"
        and violation.imported_package.startswith("app.core.companion_harness")
        for violation in violations
    )


def test_cli_json_output(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _init_repo(repo_root)
    _seed_mini_repo(repo_root)
    subprocess.run(["git", "add", "."], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "seed"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    _write(repo_root / "backend" / "ops" / "channel.py", "VALUE = 2\n")
    subprocess.run(["git", "add", "."], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "change channel"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )

    result = subprocess.run(
        [
            sys.executable,
            str(_SCRIPTS_DIR / "affected_test_packages.py"),
            "--base-ref",
            "HEAD^",
            "--head-ref",
            "HEAD",
            "--repo-root",
            str(repo_root),
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["run_all"] is False
    assert "tests.backend.ops" in payload["affected_test_packages"]
