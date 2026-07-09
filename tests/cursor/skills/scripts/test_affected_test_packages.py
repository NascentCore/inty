"""Tests for affected_test_packages selective pytest planning."""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[4] / ".cursor" / "skills" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from affected_test_packages import (  # noqa: E402
    ImportGraph,
    REPL_REGRESSION_TEST_DIR,
    build_import_graph,
    select_affected_tests,
    _coupled_regression_test_dirs,
    _mirror_test_package,
    _pytest_paths,
    _reverse_index,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _seed_mini_repo(repo_root: Path) -> None:
    _write(repo_root / "app" / "alpha" / "core.py", "VALUE = 1\n")
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
        repo_root / "tests" / "app" / "beta" / "companion_test_fixtures.py",
        "SHARED = True\n",
    )
    _write(
        repo_root / "tests" / "app" / "gamma" / "test_gamma.py",
        "from tests.app.beta.companion_test_fixtures import SHARED\n",
    )
    _write(repo_root / "app" / "living_sphere" / "models.py", "MODEL = 'living'\n")
    _write(
        repo_root / "tests" / "living_sphere" / "test_models.py",
        "from app.living_sphere.models import MODEL\n",
    )
    for index in range(8):
        _write(
            repo_root / "tests" / "isolated" / f"pkg{index}" / "test_isolated.py",
            f"ISOLATED_{index} = {index}\n",
        )


def test_reverse_bfs_selects_transitive_test_packages(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _seed_mini_repo(repo_root)
    graph = build_import_graph(repo_root)
    reverse = _reverse_index(graph)
    plan = select_affected_tests(
        repo_root,
        ("app/alpha/core.py",),
        graph,
        reverse,
    )
    assert plan.run_all is False
    assert "tests.app.alpha" in plan.affected_test_packages
    assert "tests.app.beta" in plan.affected_test_packages
    assert "tests.backend.ops" in plan.affected_test_packages


def test_living_sphere_mirror_and_test_selection(tmp_path: Path) -> None:
    assert _mirror_test_package("app.living_sphere.models") == "tests.living_sphere.models"
    repo_root = tmp_path / "repo"
    _seed_mini_repo(repo_root)
    graph = build_import_graph(repo_root)
    plan = select_affected_tests(
        repo_root,
        ("app/living_sphere/models.py",),
        graph,
        _reverse_index(graph),
    )
    assert plan.run_all is False
    assert "tests.living_sphere" in plan.affected_test_packages


def test_test_to_test_fixture_chain(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _seed_mini_repo(repo_root)
    graph = build_import_graph(repo_root)
    plan = select_affected_tests(
        repo_root,
        ("tests/app/beta/companion_test_fixtures.py",),
        graph,
        _reverse_index(graph),
    )
    assert plan.run_all is False
    assert "tests.app.gamma" in plan.affected_test_packages


def test_global_change_triggers_full_suite(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _seed_mini_repo(repo_root)
    graph = build_import_graph(repo_root)
    plan = select_affected_tests(
        repo_root,
        ("tests/conftest.py",),
        graph,
        _reverse_index(graph),
    )
    assert plan.run_all is True
    assert plan.full_suite_reason == "global_change"


def test_ratio_threshold_triggers_full_suite(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    graph = ImportGraph()
    test_packages = [f"tests.pkg{i}" for i in range(10)]
    for name in test_packages:
        graph.forward[name] = set()
    reverse = {"tests.pkg0": set(test_packages[1:])}
    _write(repo_root / "tests" / "pkg0" / "module.py", "VALUE = 1\n")
    plan = select_affected_tests(
        repo_root,
        ("tests/pkg0/module.py",),
        graph,
        reverse,
    )
    assert plan.run_all is True
    assert plan.full_suite_reason == "ratio_threshold"


def test_pytest_paths_prune_parent_when_child_selected(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _write(repo_root / "tests" / "app" / "root_case.py", "X = 1\n")
    _write(repo_root / "tests" / "app" / "child" / "test_child.py", "X = 1\n")
    paths = _pytest_paths({"tests.app", "tests.app.child"}, repo_root)
    assert "tests/app/child" in paths
    assert "tests/app" not in paths
    assert "tests/app/root_case.py" in paths


def test_sim_transport_change_couples_repl_regression_tests(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _seed_mini_repo(repo_root)
    _write(
        repo_root / "tools" / "inty_v2_repl" / "sim_transport.py",
        "VALUE = 1\n",
    )
    _write(
        repo_root / "tests" / "tools" / "inty_v2_repl" / "test_sim_transport.py",
        "from tools.inty_v2_repl import sim_transport\n",
    )
    graph = build_import_graph(repo_root)
    changed = ("tools/inty_v2_repl/sim_transport.py",)
    plan = select_affected_tests(
        repo_root,
        changed,
        graph,
        _reverse_index(graph),
    )
    assert plan.run_all is False
    assert REPL_REGRESSION_TEST_DIR in plan.test_dirs


def test_regression_driver_change_couples_repl_regression_tests(tmp_path: Path) -> None:
    coupled = _coupled_regression_test_dirs(
        (".cursor/skills/scripts/run_inty_repl_regression.py",),
        set(),
    )
    assert coupled == {REPL_REGRESSION_TEST_DIR}
