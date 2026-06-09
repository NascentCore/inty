"""Architecture tests for companion AwakeTurn / DreamingBatch invariants."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_checker_module():
    repo_root = Path(__file__).resolve().parents[5]
    script_path = (
        repo_root
        / ".cursor/skills/scripts/check_companion_turn_invariants.py"
    )
    module_name = "check_companion_turn_invariants"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return repo_root, module


def test_companion_turn_invariants_architecture() -> None:
    repo_root, checker = _load_checker_module()
    violations = checker.collect_violations(repo_root)
    assert violations == [], "\n".join(
        f"{v.file_path}:{v.line_number} rule={v.rule} detail={v.detail}"
        for v in violations
    )
